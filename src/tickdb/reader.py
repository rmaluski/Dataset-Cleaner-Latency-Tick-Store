"""
High-performance data reader for the data lake.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from pydantic import BaseModel

from .core import TickDBConfig

logger = logging.getLogger(__name__)


class QueryResult(BaseModel):
    """Result of a data query operation."""
    
    table: pa.Table
    query_time_ms: float = 0.0
    rows_returned: int = 0
    files_scanned: int = 0
    bytes_scanned: int = 0


class DataReader:
    """
    High-performance data reader for the data lake.
    
    This class provides:
    - Fast querying using DuckDB and PyArrow
    - Predicate push-down optimization
    - Column projection
    - Time-range filtering
    - Symbol-based filtering
    """
    
    def __init__(self, config: TickDBConfig):
        """
        Initialize data reader.
        
        Args:
            config: TickDB configuration
        """
        self.config = config
        self.duckdb_con = duckdb.connect(":memory:")
        
        # Register Arrow functions
        self.duckdb_con.install_extension("arrow")
        self.duckdb_con.load_extension("arrow")
        
        logger.info("Data reader initialized")
    
    def query(self, query_params: Dict[str, Any]) -> pa.Table:
        """
        Execute a query against the data lake.
        
        Args:
            query_params: Query parameters including filters and projections
            
        Returns:
            Arrow Table with query results
        """
        start_time = datetime.now()
        
        logger.info("Executing query", extra=query_params)
        
        try:
            # Build query
            query = self._build_query(query_params)
            
            # Execute query
            result = self._execute_query(query, query_params)
            
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info("Query completed", extra={
                "query_time_ms": query_time,
                "rows_returned": len(result.table),
                "files_scanned": result.files_scanned
            })
            
            return result.table
            
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            raise
    
    def _build_query(self, query_params: Dict[str, Any]) -> str:
        """Build SQL query from parameters."""
        
        # Get schema and fields
        schema_id = query_params.get("schema_id", "ticks_v1")
        fields = query_params.get("fields", ["*"])
        
        # Build field list
        if fields == ["*"]:
            field_list = "*"
        else:
            field_list = ", ".join(fields)
        
        # Build WHERE clause
        where_conditions = []
        
        # Symbol filter
        if symbol := query_params.get("symbol"):
            where_conditions.append(f"symbol = '{symbol}'")
        
        # Time range filter
        if ts_start := query_params.get("ts_start"):
            where_conditions.append(f"ts >= '{ts_start}'")
        
        if ts_end := query_params.get("ts_end"):
            where_conditions.append(f"ts <= '{ts_end}'")
        
        # Source filter
        if source_id := query_params.get("source_id"):
            where_conditions.append(f"source_id = '{source_id}'")
        
        # Additional filters
        for key, value in query_params.items():
            if key not in ["schema_id", "fields", "symbol", "ts_start", "ts_end", "source_id"]:
                if isinstance(value, str):
                    where_conditions.append(f"{key} = '{value}'")
                else:
                    where_conditions.append(f"{key} = {value}")
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        # Build ORDER BY clause
        order_by = query_params.get("order_by", "ts")
        order_clause = f"ORDER BY {order_by}"
        
        # Build LIMIT clause
        limit = query_params.get("limit")
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        # Build complete query
        query = f"""
        SELECT {field_list}
        FROM read_parquet('{self.config.data_path}/{schema_id}/*.parquet')
        {where_clause}
        {order_clause}
        {limit_clause}
        """
        
        return query.strip()
    
    def _execute_query(self, query: str, query_params: Dict[str, Any]) -> QueryResult:
        """Execute the SQL query."""
        start_time = datetime.now()
        
        # Execute query
        result = self.duckdb_con.execute(query)
        table = result.arrow()
        
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Count files scanned
        schema_id = query_params.get("schema_id", "ticks_v1")
        files_scanned = self._count_files_scanned(schema_id, query_params)
        
        return QueryResult(
            table=table,
            query_time_ms=query_time,
            rows_returned=len(table),
            files_scanned=files_scanned,
            bytes_scanned=0  # Could be calculated from file sizes
        )
    
    def _count_files_scanned(self, schema_id: str, query_params: Dict[str, Any]) -> int:
        """Count number of files that would be scanned."""
        schema_path = self.config.data_path / schema_id
        
        if not schema_path.exists():
            return 0
        
        # Simple file counting - in production, this would use metadata
        parquet_files = list(schema_path.glob("*.parquet"))
        return len(parquet_files)
    
    def read_time_slice(
        self,
        symbol: str,
        ts_start: Union[str, datetime],
        ts_end: Union[str, datetime],
        schema_id: str = "ticks_v1",
        fields: Optional[List[str]] = None,
        **kwargs: Any
    ) -> pa.Table:
        """
        Read data for a specific symbol and time range.
        
        Args:
            symbol: Trading symbol
            ts_start: Start timestamp
            ts_end: End timestamp
            schema_id: Schema identifier
            fields: Fields to return
            **kwargs: Additional parameters
            
        Returns:
            Arrow Table with results
        """
        query_params = {
            "schema_id": schema_id,
            "symbol": symbol,
            "ts_start": str(ts_start),
            "ts_end": str(ts_end),
            "fields": fields or ["*"],
            **kwargs
        }
        
        return self.query(query_params)
    
    def read_latest(
        self,
        symbol: str,
        limit: int = 1000,
        schema_id: str = "ticks_v1",
        fields: Optional[List[str]] = None,
        **kwargs: Any
    ) -> pa.Table:
        """
        Read latest data for a symbol.
        
        Args:
            symbol: Trading symbol
            limit: Number of rows to return
            schema_id: Schema identifier
            fields: Fields to return
            **kwargs: Additional parameters
            
        Returns:
            Arrow Table with results
        """
        query_params = {
            "schema_id": schema_id,
            "symbol": symbol,
            "fields": fields or ["*"],
            "order_by": "ts DESC",
            "limit": limit,
            **kwargs
        }
        
        return self.query(query_params)
    
    def read_symbols(
        self,
        symbols: List[str],
        ts_start: Optional[Union[str, datetime]] = None,
        ts_end: Optional[Union[str, datetime]] = None,
        schema_id: str = "ticks_v1",
        fields: Optional[List[str]] = None,
        **kwargs: Any
    ) -> pa.Table:
        """
        Read data for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            ts_start: Start timestamp
            ts_end: End timestamp
            schema_id: Schema identifier
            fields: Fields to return
            **kwargs: Additional parameters
            
        Returns:
            Arrow Table with results
        """
        # Build symbol condition
        symbol_conditions = [f"symbol = '{s}'" for s in symbols]
        symbol_clause = f"({' OR '.join(symbol_conditions)})"
        
        # Build time conditions
        time_conditions = []
        if ts_start:
            time_conditions.append(f"ts >= '{ts_start}'")
        if ts_end:
            time_conditions.append(f"ts <= '{ts_end}'")
        
        # Build WHERE clause
        where_conditions = [symbol_clause]
        where_conditions.extend(time_conditions)
        
        # Build query
        fields_str = ", ".join(fields) if fields else "*"
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT {fields_str}
        FROM read_parquet('{self.config.data_path}/{schema_id}/*.parquet')
        WHERE {where_clause}
        ORDER BY ts
        """
        
        # Execute query
        result = self.duckdb_con.execute(query)
        return result.arrow()
    
    def get_metadata(
        self,
        schema_id: str = "ticks_v1",
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get metadata about the data lake.
        
        Args:
            schema_id: Schema identifier
            symbol: Optional symbol filter
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "schema_id": schema_id,
            "total_files": 0,
            "total_rows": 0,
            "date_range": {},
            "symbols": [],
            "file_sizes": {}
        }
        
        schema_path = self.config.data_path / schema_id
        
        if not schema_path.exists():
            return metadata
        
        # Scan files for metadata
        parquet_files = list(schema_path.glob("*.parquet"))
        metadata["total_files"] = len(parquet_files)
        
        if parquet_files:
            # Read metadata from first file
            first_file = parquet_files[0]
            try:
                parquet_file = pq.ParquetFile(first_file)
                metadata["total_rows"] = parquet_file.metadata.num_rows
                
                # Get schema info
                schema = parquet_file.schema_arrow
                metadata["columns"] = [field.name for field in schema]
                
            except Exception as e:
                logger.warning(f"Failed to read metadata from {first_file}: {e}")
        
        return metadata
    
    def list_symbols(self, schema_id: str = "ticks_v1") -> List[str]:
        """
        List all symbols in the data lake.
        
        Args:
            schema_id: Schema identifier
            
        Returns:
            List of symbols
        """
        query = f"""
        SELECT DISTINCT symbol
        FROM read_parquet('{self.config.data_path}/{schema_id}/*.parquet')
        ORDER BY symbol
        """
        
        try:
            result = self.duckdb_con.execute(query)
            df = result.df()
            return df["symbol"].tolist() if not df.empty else []
        except Exception as e:
            logger.warning(f"Failed to list symbols: {e}")
            return []
    
    def get_date_range(
        self,
        symbol: Optional[str] = None,
        schema_id: str = "ticks_v1"
    ) -> Dict[str, Any]:
        """
        Get date range of data.
        
        Args:
            symbol: Optional symbol filter
            schema_id: Schema identifier
            
        Returns:
            Date range dictionary
        """
        where_clause = ""
        if symbol:
            where_clause = f"WHERE symbol = '{symbol}'"
        
        query = f"""
        SELECT 
            MIN(ts) as min_ts,
            MAX(ts) as max_ts,
            COUNT(*) as total_rows
        FROM read_parquet('{self.config.data_path}/{schema_id}/*.parquet')
        {where_clause}
        """
        
        try:
            result = self.duckdb_con.execute(query)
            df = result.df()
            
            if not df.empty:
                return {
                    "min_ts": df["min_ts"].iloc[0],
                    "max_ts": df["max_ts"].iloc[0],
                    "total_rows": df["total_rows"].iloc[0]
                }
        except Exception as e:
            logger.warning(f"Failed to get date range: {e}")
        
        return {"min_ts": None, "max_ts": None, "total_rows": 0}
    
    def close(self) -> None:
        """Close the database connection."""
        if self.duckdb_con:
            self.duckdb_con.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 