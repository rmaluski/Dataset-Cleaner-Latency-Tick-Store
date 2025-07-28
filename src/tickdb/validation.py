"""
Data validation component for the data lake.
"""

import logging
from datetime import datetime, time
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow as pa
from pydantic import BaseModel

from .config import TickDBConfig
from .schemas import SchemaDefinition

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Result of a data validation operation."""
    
    valid: bool = True
    errors: List[str] = []
    warnings: List[str] = []
    rows_checked: int = 0
    rows_failed: int = 0
    validation_time_ms: float = 0.0


class DataValidator:
    """
    Data validation component for the data lake.
    
    This class provides:
    - Schema validation
    - Data type checking
    - Range validation
    - Business rule validation
    - Duplicate detection
    - Out-of-hours timestamp detection
    """
    
    def __init__(self, config: TickDBConfig):
        """
        Initialize data validator.
        
        Args:
            config: TickDB configuration
        """
        self.config = config
        
        # Trading hours (9:30 AM - 4:00 PM ET)
        self.trading_start = time(9, 30)
        self.trading_end = time(16, 0)
        
        logger.info("Data validator initialized")
    
    def validate_table(
        self,
        table: pa.Table,
        schema: SchemaDefinition
    ) -> Dict[str, Any]:
        """
        Validate an Arrow table against a schema.
        
        Args:
            table: Arrow table to validate
            schema: Schema definition
            
        Returns:
            Validation result dictionary
        """
        start_time = datetime.now()
        
        logger.info("Validating table", extra={
            "schema_id": schema.id,
            "rows": len(table),
            "columns": len(table.column_names)
        })
        
        result = ValidationResult(rows_checked=len(table))
        
        try:
            # Schema compatibility check
            schema_result = self._validate_schema_compatibility(table, schema)
            result.errors.extend(schema_result.get("errors", []))
            result.warnings.extend(schema_result.get("warnings", []))
            
            if not schema_result.get("compatible", True):
                result.valid = False
                result.rows_failed = len(table)
                result.validation_time_ms = (
                    datetime.now() - start_time
                ).total_seconds() * 1000
                return result.model_dump()
            
            # Field-level validation
            field_result = self._validate_fields(table, schema)
            result.errors.extend(field_result.get("errors", []))
            result.warnings.extend(field_result.get("warnings", []))
            
            if field_result.get("rows_failed", 0) > 0:
                result.valid = False
                result.rows_failed = field_result["rows_failed"]
            
            # Business rule validation
            business_result = self._validate_business_rules(table, schema)
            result.errors.extend(business_result.get("errors", []))
            result.warnings.extend(business_result.get("warnings", []))
            
            if business_result.get("rows_failed", 0) > 0:
                result.valid = False
                result.rows_failed += business_result["rows_failed"]
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            result.errors.append(error_msg)
            result.valid = False
            result.rows_failed = len(table)
            logger.error(error_msg, exc_info=True)
        
        result.validation_time_ms = (
            datetime.now() - start_time
        ).total_seconds() * 1000
        
        logger.info("Validation completed", extra={
            "schema_id": schema.id,
            "valid": result.valid,
            "rows_failed": result.rows_failed,
            "validation_time_ms": result.validation_time_ms
        })
        
        return result.model_dump()
    
    def _validate_schema_compatibility(
        self,
        table: pa.Table,
        schema: SchemaDefinition
    ) -> Dict[str, Any]:
        """Validate schema compatibility."""
        result = {"compatible": True, "errors": [], "warnings": []}
        
        # Check required fields
        required_fields = {
            field.name for field in schema.fields 
            if not field.nullable
        }
        
        table_fields = set(table.column_names)
        missing_fields = required_fields - table_fields
        
        if missing_fields:
            result["compatible"] = False
            result["errors"].append(
                f"Missing required fields: {missing_fields}"
            )
        
        # Check field types for common fields
        for field_def in schema.fields:
            if field_def.name in table.column_names:
                table_field = table.schema.field(field_def.name)
                expected_type = self._parse_arrow_type(field_def.type)
                
                if not table_field.type.equals(expected_type):
                    result["warnings"].append(
                        f"Type mismatch for field '{field_def.name}': "
                        f"expected {expected_type}, got {table_field.type}"
                    )
        
        return result
    
    def _validate_fields(
        self,
        table: pa.Table,
        schema: SchemaDefinition
    ) -> Dict[str, Any]:
        """Validate individual fields."""
        result = {"errors": [], "warnings": [], "rows_failed": 0}
        
        for field_def in schema.fields:
            if field_def.name in table.column_names:
                field_result = self._validate_field(
                    table, field_def
                )
                result["errors"].extend(field_result.get("errors", []))
                result["warnings"].extend(field_result.get("warnings", []))
                result["rows_failed"] += field_result.get("rows_failed", 0)
        
        return result
    
    def _validate_field(
        self,
        table: pa.Table,
        field_def: Any
    ) -> Dict[str, Any]:
        """Validate a single field."""
        result = {"errors": [], "warnings": [], "rows_failed": 0}
        
        column = table.column(field_def.name)
        
        # Check for null values in non-nullable fields
        if not field_def.nullable:
            null_count = column.null_count
            if null_count > 0:
                result["errors"].append(
                    f"Field '{field_def.name}' has {null_count} null values "
                    "but is marked as non-nullable"
                )
                result["rows_failed"] += null_count
        
        # Check constraints if defined
        if field_def.constraints:
            constraint_result = self._validate_constraints(
                column, field_def.constraints
            )
            result["errors"].extend(constraint_result.get("errors", []))
            result["warnings"].extend(constraint_result.get("warnings", []))
            result["rows_failed"] += constraint_result.get("rows_failed", 0)
        
        return result
    
    def _validate_constraints(
        self,
        column: pa.ChunkedArray,
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate field constraints."""
        result = {"errors": [], "warnings": [], "rows_failed": 0}
        
        # Convert to pandas for easier validation
        try:
            series = column.to_pandas()
        except Exception as e:
            result["errors"].append(f"Failed to convert column to pandas: {e}")
            return result
        
        # Min/max value constraints
        if "min_value" in constraints:
            min_val = constraints["min_value"]
            below_min = series < min_val
            if below_min.any():
                count = below_min.sum()
                result["errors"].append(
                    f"{count} values below minimum {min_val}"
                )
                result["rows_failed"] += count
        
        if "max_value" in constraints:
            max_val = constraints["max_value"]
            above_max = series > max_val
            if above_max.any():
                count = above_max.sum()
                result["errors"].append(
                    f"{count} values above maximum {max_val}"
                )
                result["rows_failed"] += count
        
        # String length constraints
        if "min_length" in constraints and series.dtype == "object":
            min_len = constraints["min_length"]
            short_strings = series.str.len() < min_len
            if short_strings.any():
                count = short_strings.sum()
                result["errors"].append(
                    f"{count} strings shorter than {min_len} characters"
                )
                result["rows_failed"] += count
        
        if "max_length" in constraints and series.dtype == "object":
            max_len = constraints["max_length"]
            long_strings = series.str.len() > max_len
            if long_strings.any():
                count = long_strings.sum()
                result["errors"].append(
                    f"{count} strings longer than {max_len} characters"
                )
                result["rows_failed"] += count
        
        # Pattern constraints for strings
        if "pattern" in constraints and series.dtype == "object":
            import re
            pattern = constraints["pattern"]
            try:
                regex = re.compile(pattern)
                invalid_patterns = ~series.str.match(regex, na=False)
                if invalid_patterns.any():
                    count = invalid_patterns.sum()
                    result["errors"].append(
                        f"{count} values don't match pattern {pattern}"
                    )
                    result["rows_failed"] += count
            except Exception as e:
                result["errors"].append(f"Invalid regex pattern {pattern}: {e}")
        
        return result
    
    def _validate_business_rules(
        self,
        table: pa.Table,
        schema: SchemaDefinition
    ) -> Dict[str, Any]:
        """Validate business rules."""
        result = {"errors": [], "warnings": [], "rows_failed": 0}
        
        # Timestamp validation for tick data
        if schema.id == "ticks_v1" and "ts" in table.column_names:
            ts_result = self._validate_timestamps(table)
            result["errors"].extend(ts_result.get("errors", []))
            result["warnings"].extend(ts_result.get("warnings", []))
            result["rows_failed"] += ts_result.get("rows_failed", 0)
        
        # Price validation for tick data
        if schema.id == "ticks_v1" and "price" in table.column_names:
            price_result = self._validate_prices(table)
            result["errors"].extend(price_result.get("errors", []))
            result["warnings"].extend(price_result.get("warnings", []))
            result["rows_failed"] += price_result.get("rows_failed", 0)
        
        # Size validation for tick data
        if schema.id == "ticks_v1" and "size" in table.column_names:
            size_result = self._validate_sizes(table)
            result["errors"].extend(size_result.get("errors", []))
            result["warnings"].extend(size_result.get("warnings", []))
            result["rows_failed"] += size_result.get("rows_failed", 0)
        
        # Duplicate detection
        duplicate_result = self._detect_duplicates(table, schema)
        result["warnings"].extend(duplicate_result.get("warnings", []))
        
        return result
    
    def _validate_timestamps(self, table: pa.Table) -> Dict[str, Any]:
        """Validate timestamp data."""
        result = {"errors": [], "warnings": [], "rows_failed": 0}
        
        try:
            ts_series = table.column("ts").to_pandas()
            
            # Check for future timestamps
            now = pd.Timestamp.now()
            future_ts = ts_series > now
            if future_ts.any():
                count = future_ts.sum()
                result["warnings"].append(
                    f"{count} timestamps are in the future"
                )
            
            # Check for out-of-hours timestamps
            if "symbol" in table.column_names:
                symbol_series = table.column("symbol").to_pandas()
                out_of_hours = self._detect_out_of_hours(ts_series, symbol_series)
                if out_of_hours.any():
                    count = out_of_hours.sum()
                    result["warnings"].append(
                        f"{count} timestamps are outside trading hours"
                    )
            
            # Check for duplicate timestamps
            duplicates = ts_series.duplicated()
            if duplicates.any():
                count = duplicates.sum()
                result["warnings"].append(
                    f"{count} duplicate timestamps detected"
                )
            
        except Exception as e:
            result["errors"].append(f"Timestamp validation failed: {e}")
            result["rows_failed"] = len(table)
        
        return result
    
    def _validate_prices(self, table: pa.Table) -> Dict[str, Any]:
        """Validate price data."""
        result = {"errors": [], "warnings": [], "rows_failed": 0}
        
        try:
            price_series = table.column("price").to_pandas()
            
            # Check for negative prices
            negative_prices = price_series < 0
            if negative_prices.any():
                count = negative_prices.sum()
                result["errors"].append(
                    f"{count} negative prices detected"
                )
                result["rows_failed"] += count
            
            # Check for zero prices
            zero_prices = price_series == 0
            if zero_prices.any():
                count = zero_prices.sum()
                result["warnings"].append(
                    f"{count} zero prices detected"
                )
            
            # Check for extreme price changes (if we have multiple prices)
            if len(price_series) > 1:
                price_changes = price_series.pct_change().abs()
                extreme_changes = price_changes > 0.1  # 10% change
                if extreme_changes.any():
                    count = extreme_changes.sum()
                    result["warnings"].append(
                        f"{count} extreme price changes (>10%) detected"
                    )
            
        except Exception as e:
            result["errors"].append(f"Price validation failed: {e}")
            result["rows_failed"] = len(table)
        
        return result
    
    def _validate_sizes(self, table: pa.Table) -> Dict[str, Any]:
        """Validate size data."""
        result = {"errors": [], "warnings": [], "rows_failed": 0}
        
        try:
            size_series = table.column("size").to_pandas()
            
            # Check for negative sizes
            negative_sizes = size_series < 0
            if negative_sizes.any():
                count = negative_sizes.sum()
                result["errors"].append(
                    f"{count} negative sizes detected"
                )
                result["rows_failed"] += count
            
            # Check for zero sizes
            zero_sizes = size_series == 0
            if zero_sizes.any():
                count = zero_sizes.sum()
                result["warnings"].append(
                    f"{count} zero sizes detected"
                )
            
            # Check for extremely large sizes
            large_sizes = size_series > 1000000  # 1M shares
            if large_sizes.any():
                count = large_sizes.sum()
                result["warnings"].append(
                    f"{count} extremely large sizes (>1M) detected"
                )
            
        except Exception as e:
            result["errors"].append(f"Size validation failed: {e}")
            result["rows_failed"] = len(table)
        
        return result
    
    def _detect_out_of_hours(
        self,
        ts_series: pd.Series,
        symbol_series: pd.Series
    ) -> pd.Series:
        """Detect timestamps outside trading hours."""
        # Convert to ET timezone and extract time
        try:
            et_series = ts_series.dt.tz_convert("US/Eastern")
            times = et_series.dt.time
            
            # Check if outside trading hours
            out_of_hours = (times < self.trading_start) | (times > self.trading_end)
            
            return out_of_hours
        except Exception:
            # If timezone conversion fails, return all False
            return pd.Series([False] * len(ts_series))
    
    def _detect_duplicates(
        self,
        table: pa.Table,
        schema: SchemaDefinition
    ) -> Dict[str, Any]:
        """Detect duplicate records."""
        result = {"warnings": []}
        
        try:
            # For tick data, check for duplicate ts+symbol combinations
            if schema.id == "ticks_v1" and "ts" in table.column_names and "symbol" in table.column_names:
                ts_series = table.column("ts").to_pandas()
                symbol_series = table.column("symbol").to_pandas()
                
                # Create composite key
                composite_key = ts_series.astype(str) + "_" + symbol_series
                duplicates = composite_key.duplicated()
                
                if duplicates.any():
                    count = duplicates.sum()
                    result["warnings"].append(
                        f"{count} duplicate ts+symbol combinations detected"
                    )
        
        except Exception as e:
            result["warnings"].append(f"Duplicate detection failed: {e}")
        
        return result
    
    def _parse_arrow_type(self, type_str: str) -> pa.DataType:
        """Parse Arrow type string to Arrow DataType."""
        type_mapping = {
            "string": pa.string(),
            "int8": pa.int8(),
            "int16": pa.int16(),
            "int32": pa.int32(),
            "int64": pa.int64(),
            "uint8": pa.uint8(),
            "uint16": pa.uint16(),
            "uint32": pa.uint32(),
            "uint64": pa.uint64(),
            "float32": pa.float32(),
            "float64": pa.float64(),
            "boolean": pa.bool_(),
            "timestamp[ns]": pa.timestamp("ns"),
            "timestamp[us]": pa.timestamp("us"),
            "timestamp[ms]": pa.timestamp("ms"),
            "timestamp[s]": pa.timestamp("s"),
            "date32": pa.date32(),
            "date64": pa.date64(),
            "time32[s]": pa.time32("s"),
            "time32[ms]": pa.time32("ms"),
            "time64[us]": pa.time64("us"),
            "time64[ns]": pa.time64("ns"),
        }
        
        if type_str in type_mapping:
            return type_mapping[type_str]
        
        # Handle complex types
        if type_str.startswith("list<") and type_str.endswith(">"):
            inner_type = type_str[5:-1]
            return pa.list_(self._parse_arrow_type(inner_type))
        
        if type_str.startswith("struct<") and type_str.endswith(">"):
            return pa.struct([])
        
        raise ValueError(f"Unsupported Arrow type: {type_str}") 