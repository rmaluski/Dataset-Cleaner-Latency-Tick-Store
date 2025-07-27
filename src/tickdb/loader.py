"""
High-performance data loader for the data lake.
"""

import gzip
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.parquet as pq
from pydantic import BaseModel

from .core import TickDBConfig
from .schemas import SchemaDefinition

# Try to import C++ and Rust components for high performance
try:
    from . import dataset_core_python as cpp_core
    HAS_CPP = True
except ImportError:
    HAS_CPP = False
    logger = logging.getLogger(__name__)
    logger.warning("C++ components not available, using Python fallback")

try:
    from . import dataset_core_rust as rust_core
    HAS_RUST = True
except ImportError:
    HAS_RUST = False
    logger = logging.getLogger(__name__)
    logger.warning("Rust components not available, using Python fallback")

logger = logging.getLogger(__name__)


class LoadResult(BaseModel):
    """Result of a data loading operation."""
    
    rows_processed: int = 0
    rows_failed: int = 0
    bytes_processed: int = 0
    files_created: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    processing_time_ms: float = 0.0


class DataLoader:
    """
    High-performance data loader for the data lake.
    
    This class handles:
    - File format detection and parsing
    - Batch processing with Arrow
    - Parquet file writing with partitioning
    - Compression and optimization
    - Error handling and quarantine
    """
    
    def __init__(self, config: TickDBConfig):
        """
        Initialize data loader.
        
        Args:
            config: TickDB configuration
        """
        self.config = config
        self.supported_formats = {".csv", ".csv.gz", ".json", ".json.gz", ".parquet"}
        
        logger.info("Data loader initialized", extra={
            "batch_size": config.batch_size,
            "compression": config.compression,
            "compression_level": config.compression_level
        })
    
    def load_file(
        self,
        source_id: str,
        file_path: Union[str, Path],
        schema: SchemaDefinition,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Load a file into the data lake.
        
        Args:
            source_id: Data source identifier
            file_path: Path to the file to load
            schema: Schema definition for validation
            **kwargs: Additional arguments
            
        Returns:
            Load result dictionary
        """
        file_path = Path(file_path)
        start_time = datetime.now()
        
        logger.info("Loading file", extra={
            "source_id": source_id,
            "file_path": str(file_path),
            "schema_id": schema.id
        })
        
        result = LoadResult()
        
        try:
            # Detect file format
            file_format = self._detect_format(file_path)
            
            # Read file into Arrow table
            table = self._read_file(file_path, file_format, **kwargs)
            result.bytes_processed = file_path.stat().st_size
            
            # Add metadata columns
            table = self._add_metadata(table, source_id)
            
            # Validate and process
            processed_result = self._process_table(table, schema, source_id)
            
            # Merge results
            result.rows_processed = processed_result.rows_processed
            result.rows_failed = processed_result.rows_failed
            result.files_created = processed_result.files_created
            result.errors = processed_result.errors
            result.warnings = processed_result.warnings
            
        except Exception as e:
            error_msg = f"Failed to load file {file_path}: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
        
        result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info("File load completed", extra={
            "source_id": source_id,
            "file_path": str(file_path),
            "rows_processed": result.rows_processed,
            "rows_failed": result.rows_failed,
            "processing_time_ms": result.processing_time_ms
        })
        
        return result.model_dump()
    
    def store_table(
        self,
        table: pa.Table,
        schema_id: str,
        source_id: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Store an Arrow table in the data lake.
        
        Args:
            table: Arrow table to store
            schema_id: Schema identifier
            source_id: Optional source identifier
            **kwargs: Additional arguments
            
        Returns:
            Store result dictionary
        """
        start_time = datetime.now()
        
        logger.info("Storing table", extra={
            "schema_id": schema_id,
            "source_id": source_id,
            "rows": len(table)
        })
        
        result = LoadResult()
        
        try:
            # Add metadata if not present
            if "source_id" not in table.column_names and source_id:
                table = self._add_metadata(table, source_id)
            
            # Get schema for partitioning
            from .schemas import SchemaRegistry
            schema_registry = SchemaRegistry()
            schema = schema_registry.get_schema(schema_id)
            
            # Process and store
            processed_result = self._process_table(table, schema, source_id or "unknown")
            
            result.rows_processed = processed_result.rows_processed
            result.rows_failed = processed_result.rows_failed
            result.files_created = processed_result.files_created
            result.errors = processed_result.errors
            result.warnings = processed_result.warnings
            
        except Exception as e:
            error_msg = f"Failed to store table: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
        
        result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return result.model_dump()
    
    def _detect_format(self, file_path: Path) -> str:
        """Detect file format based on extension."""
        suffix = file_path.suffix.lower()
        if suffix == ".gz":
            suffix = file_path.stem + suffix
        
        if suffix not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        return suffix
    
    def _read_file(
        self,
        file_path: Path,
        file_format: str,
        **kwargs: Any
    ) -> pa.Table:
        """Read file into Arrow table based on format."""
        
        if file_format == ".csv":
            return self._read_csv(file_path, **kwargs)
        elif file_format == ".csv.gz":
            return self._read_csv_gz(file_path, **kwargs)
        elif file_format == ".json":
            return self._read_json(file_path, **kwargs)
        elif file_format == ".json.gz":
            return self._read_json_gz(file_path, **kwargs)
        elif file_format == ".parquet":
            return self._read_parquet(file_path, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {file_format}")
    
    def _read_csv(self, file_path: Path, **kwargs: Any) -> pa.Table:
        """Read CSV file with high-performance components if available."""
        
        # Try to use C++ SIMD parser for maximum performance
        if HAS_CPP:
            try:
                logger.info("Using C++ SIMD parser for CSV reading")
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                parser = cpp_core.SimdParser()
                delimiter = kwargs.get("delimiter", ",").encode()[0]
                batch_size = kwargs.get("batch_size", self.config.batch_size)
                
                table = parser.parse_csv_simd(data, delimiter, batch_size)
                stats = parser.get_stats()
                logger.info("C++ parsing completed", extra=stats)
                return table
            except Exception as e:
                logger.warning(f"C++ parser failed, falling back to Python: {e}")
        
        # Try to use Rust parser as fallback
        if HAS_RUST:
            try:
                logger.info("Using Rust parser for CSV reading")
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                parser = rust_core.SimdParser()
                delimiter = kwargs.get("delimiter", ",")
                batch_size = kwargs.get("batch_size", self.config.batch_size)
                
                table = parser.parse_csv_py(data, delimiter, batch_size)
                stats = parser.get_stats_py()
                logger.info("Rust parsing completed", extra=stats)
                return table
            except Exception as e:
                logger.warning(f"Rust parser failed, falling back to Python: {e}")
        
        # Fallback to standard Arrow CSV reader
        logger.info("Using standard Arrow CSV reader")
        read_options = csv.ReadOptions(
            skip_rows=kwargs.get("skip_rows", 0),
            column_names=kwargs.get("column_names"),
            batch_size=self.config.batch_size
        )
        
        parse_options = csv.ParseOptions(
            delimiter=kwargs.get("delimiter", ","),
            quote_char=kwargs.get("quote_char", '"'),
            escape_char=kwargs.get("escape_char", False),
            newlines_in_values=kwargs.get("newlines_in_values", False)
        )
        
        convert_options = csv.ConvertOptions(
            strings_can_be_null=kwargs.get("strings_can_be_null", True),
            null_values=kwargs.get("null_values", [""]),
            true_values=kwargs.get("true_values", ["true", "True", "TRUE"]),
            false_values=kwargs.get("false_values", ["false", "False", "FALSE"])
        )
        
        return csv.read_csv(
            file_path,
            read_options=read_options,
            parse_options=parse_options,
            convert_options=convert_options
        )
    
    def _read_csv_gz(self, file_path: Path, **kwargs: Any) -> pa.Table:
        """Read gzipped CSV file."""
        with gzip.open(file_path, "rt") as f:
            # Create a temporary file for Arrow to read
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
                tmp.write(f.read())
                tmp_path = tmp.name
            
            try:
                return self._read_csv(Path(tmp_path), **kwargs)
            finally:
                os.unlink(tmp_path)
    
    def _read_json(self, file_path: Path, **kwargs: Any) -> pa.Table:
        """Read JSON file."""
        return pa.json.read_json(file_path)
    
    def _read_json_gz(self, file_path: Path, **kwargs: Any) -> pa.Table:
        """Read gzipped JSON file."""
        with gzip.open(file_path, "rt") as f:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                tmp.write(f.read())
                tmp_path = tmp.name
            
            try:
                return self._read_json(Path(tmp_path), **kwargs)
            finally:
                os.unlink(tmp_path)
    
    def _read_parquet(self, file_path: Path, **kwargs: Any) -> pa.Table:
        """Read Parquet file."""
        return pq.read_table(file_path)
    
    def _add_metadata(self, table: pa.Table, source_id: str) -> pa.Table:
        """Add metadata columns to table."""
        now = datetime.now(timezone.utc)
        ingest_ts = pa.array([now] * len(table), type=pa.timestamp("ns"))
        
        # Add source_id column if not present
        if "source_id" not in table.column_names:
            source_id_array = pa.array([source_id] * len(table))
            table = table.append_column("source_id", source_id_array)
        
        # Add ingest_ts column if not present
        if "ingest_ts" not in table.column_names:
            table = table.append_column("ingest_ts", ingest_ts)
        
        return table
    
    def _process_table(
        self,
        table: pa.Table,
        schema: SchemaDefinition,
        source_id: str
    ) -> LoadResult:
        """Process table and write to partitioned Parquet files."""
        result = LoadResult()
        
        try:
            # Validate table against schema
            from .validation import DataValidator
            validator = DataValidator(self.config)
            validation_result = validator.validate_table(table, schema)
            
            if validation_result["valid"]:
                # Write valid data
                files_created = self._write_partitioned_parquet(
                    table, schema, source_id
                )
                result.files_created = files_created
                result.rows_processed = len(table)
            else:
                # Handle invalid data
                result.rows_failed = len(table)
                result.errors.extend(validation_result["errors"])
                
                # Quarantine invalid data
                self._quarantine_table(table, source_id, validation_result["errors"])
            
            result.warnings.extend(validation_result.get("warnings", []))
            
        except Exception as e:
            result.rows_failed = len(table)
            result.errors.append(str(e))
            logger.error(f"Failed to process table: {e}", exc_info=True)
        
        return result
    
    def _write_partitioned_parquet(
        self,
        table: pa.Table,
        schema: SchemaDefinition,
        source_id: str
    ) -> List[str]:
        """Write table to partitioned Parquet files."""
        files_created = []
        
        # Get partition columns
        partition_cols = schema.partition_by or []
        
        if not partition_cols:
            # No partitioning, write single file
            file_path = self._get_output_path(schema.id, source_id)
            self._write_parquet_file(table, file_path)
            files_created.append(str(file_path))
        else:
            # Partitioned write
            # For now, implement simple partitioning
            # In production, this would use Arrow's partitioning capabilities
            
            # Extract date from timestamp for partitioning
            if "ts" in table.column_names and "dt" not in table.column_names:
                # Add date column for partitioning
                ts_array = table.column("ts")
                if pa.types.is_timestamp(ts_array.type):
                    # Convert timestamp to date
                    date_array = ts_array.cast(pa.date32())
                    table = table.append_column("dt", date_array)
            
            # Group by partition columns and write separate files
            # This is a simplified implementation
            file_path = self._get_output_path(schema.id, source_id)
            self._write_parquet_file(table, file_path)
            files_created.append(str(file_path))
        
        return files_created
    
    def _write_parquet_file(self, table: pa.Table, file_path: Path) -> None:
        """Write table to Parquet file with compression."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        pq.write_table(
            table,
            file_path,
            compression=self.config.compression,
            compression_level=self.config.compression_level,
            row_group_size=self.config.batch_size,
            use_dictionary=True,
            write_statistics=True
        )
        
        logger.debug("Wrote Parquet file", extra={
            "file_path": str(file_path),
            "rows": len(table),
            "size_mb": file_path.stat().st_size / (1024 * 1024)
        })
    
    def _get_output_path(self, schema_id: str, source_id: str) -> Path:
        """Generate output file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{schema_id}_{source_id}_{timestamp}.parquet"
        return self.config.data_path / schema_id / filename
    
    def _quarantine_table(
        self,
        table: pa.Table,
        source_id: str,
        errors: List[str]
    ) -> None:
        """Quarantine invalid table data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quarantine_{source_id}_{timestamp}.parquet"
        file_path = self.config.quarantine_path / filename
        
        # Add error information to table
        error_array = pa.array(["; ".join(errors)] * len(table))
        table_with_errors = table.append_column("_errors", error_array)
        
        # Write to quarantine
        file_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table_with_errors, file_path)
        
        logger.warning("Quarantined invalid data", extra={
            "file_path": str(file_path),
            "rows": len(table),
            "errors": errors
        }) 