"""
Core TickDB class that orchestrates the data lake system.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pyarrow as pa
from .config import TickDBConfig
from .loader import DataLoader
from .reader import DataReader
from .schemas import SchemaRegistry
from .validation import DataValidator
from .metrics import MetricsCollector

logger = logging.getLogger(__name__)


class TickDB:
    """
    High-throughput data lake for financial tick data.
    
    This class orchestrates the entire data lake system, providing a unified
    interface for loading, validating, storing, and querying financial data.
    """
    
    def __init__(self, config: Optional[TickDBConfig] = None):
        """
        Initialize TickDB with configuration.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or TickDBConfig()
        
        # Ensure directories exist
        self.config.data_path.mkdir(parents=True, exist_ok=True)
        self.config.quarantine_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.schema_registry = SchemaRegistry()
        self.loader = DataLoader(self.config)
        self.reader = DataReader(self.config)
        self.validator = DataValidator(self.config)
        self.metrics = MetricsCollector(enable_server=False) if self.config.enable_metrics else None
        
        logger.info("TickDB initialized", extra={
            "data_path": str(self.config.data_path),
            "batch_size": self.config.batch_size,
            "compression": self.config.compression
        })
    
    def load_raw(
        self,
        source_id: str,
        path: Union[str, Path],
        schema_id: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Load raw data file into the data lake.
        
        Args:
            source_id: Unique identifier for the data source
            path: Path to the raw data file (local or S3)
            schema_id: Schema identifier for validation
            **kwargs: Additional arguments passed to loader
            
        Returns:
            Dictionary with load statistics
        """
        logger.info("Loading raw data", extra={
            "source_id": source_id,
            "path": str(path),
            "schema_id": schema_id
        })
        
        # Get schema for validation
        schema = self.schema_registry.get_schema(schema_id)
        
        # Load and validate data
        result = self.loader.load_file(
            source_id=source_id,
            file_path=path,
            schema=schema,
            **kwargs
        )
        
        # Update metrics
        if self.metrics:
            self.metrics.record_ingest(
                source_id=source_id,
                bytes_processed=result.get("bytes_processed", 0),
                rows_processed=result.get("rows_processed", 0),
                rows_failed=result.get("rows_failed", 0)
            )
        
        return result
    
    def append(
        self,
        df: pd.DataFrame,
        schema_id: str,
        source_id: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Append pandas DataFrame to the data lake.
        
        Args:
            df: DataFrame to append
            schema_id: Schema identifier for validation
            source_id: Optional source identifier
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with append statistics
        """
        logger.info("Appending DataFrame", extra={
            "schema_id": schema_id,
            "source_id": source_id,
            "rows": len(df)
        })
        
        # Get schema for validation
        schema = self.schema_registry.get_schema(schema_id)
        
        # Convert to Arrow and validate
        table = pa.Table.from_pandas(df)
        validated_table = self.validator.validate_table(table, schema)
        
        # Store data
        result = self.loader.store_table(
            table=validated_table,
            schema_id=schema_id,
            source_id=source_id,
            **kwargs
        )
        
        # Update metrics
        if self.metrics:
            self.metrics.record_append(
                schema_id=schema_id,
                rows_processed=len(df),
                rows_failed=result.get("rows_failed", 0)
            )
        
        return result
    
    def read(
        self,
        symbol: Optional[str] = None,
        ts_start: Optional[str] = None,
        ts_end: Optional[str] = None,
        fields: Optional[List[str]] = None,
        schema_id: Optional[str] = None,
        **kwargs: Any
    ) -> pa.Table:
        """
        Read data from the data lake.
        
        Args:
            symbol: Symbol to filter by
            ts_start: Start timestamp (ISO format)
            ts_end: End timestamp (ISO format)
            fields: List of fields to return
            schema_id: Schema identifier
            **kwargs: Additional query parameters
            
        Returns:
            Arrow Table with query results
        """
        logger.info("Reading data", extra={
            "symbol": symbol,
            "ts_start": ts_start,
            "ts_end": ts_end,
            "fields": fields,
            "schema_id": schema_id
        })
        
        # Build query
        query = {
            "symbol": symbol,
            "ts_start": ts_start,
            "ts_end": ts_end,
            "fields": fields,
            "schema_id": schema_id,
            **kwargs
        }
        
        # Execute query
        start_time = pd.Timestamp.now()
        result = self.reader.query(query)
        query_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000
        
        # Update metrics
        if self.metrics:
            self.metrics.record_query(
                query_time_ms=query_time,
                rows_returned=len(result)
            )
        
        logger.info("Query completed", extra={
            "query_time_ms": query_time,
            "rows_returned": len(result)
        })
        
        return result
    
    def get_schema(self, schema_id: str) -> Dict[str, Any]:
        """Get schema definition."""
        return self.schema_registry.get_schema(schema_id)
    
    def list_schemas(self) -> List[str]:
        """List available schemas."""
        return self.schema_registry.list_schemas()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        if self.metrics:
            return self.metrics.get_metrics()
        return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health = {
            "status": "healthy",
            "components": {}
        }
        
        try:
            # Check data directory
            if not self.config.data_path.exists():
                health["status"] = "unhealthy"
                health["components"]["data_path"] = "missing"
            
            # Check schema registry
            schemas = self.list_schemas()
            health["components"]["schema_registry"] = {
                "status": "healthy",
                "schemas_count": len(schemas)
            }
            
            # Check metrics
            if self.metrics:
                health["components"]["metrics"] = {
                    "status": "healthy",
                    "metrics_count": len(self.get_metrics())
                }
            
        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)
        
        return health 