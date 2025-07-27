"""
Schema registry for managing data schemas.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pyarrow as pa
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FieldDefinition(BaseModel):
    """Definition of a single field in a schema."""
    
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Arrow data type")
    nullable: bool = Field(default=True, description="Whether field can be null")
    description: Optional[str] = Field(default=None, description="Field description")
    constraints: Optional[Dict[str, Any]] = Field(default=None, description="Validation constraints")


class SchemaDefinition(BaseModel):
    """Complete schema definition."""
    
    id: str = Field(..., description="Unique schema identifier")
    version: str = Field(default="1.0.0", description="Schema version")
    description: Optional[str] = Field(default=None, description="Schema description")
    fields: List[FieldDefinition] = Field(..., description="List of field definitions")
    partition_by: Optional[List[str]] = Field(default=None, description="Partition columns")
    sort_by: Optional[List[str]] = Field(default=None, description="Sort columns")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class SchemaRegistry:
    """
    Registry for managing data schemas.
    
    This class provides schema management functionality including:
    - Schema registration and retrieval
    - Schema validation
    - Arrow schema conversion
    - Schema versioning
    """
    
    def __init__(self, schemas_path: Optional[Path] = None):
        """
        Initialize schema registry.
        
        Args:
            schemas_path: Path to schemas directory. If None, uses default.
        """
        self.schemas_path = schemas_path or Path("./schemas")
        self.schemas_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache of loaded schemas
        self._schemas: Dict[str, SchemaDefinition] = {}
        
        # Load built-in schemas
        self._load_builtin_schemas()
        
        logger.info("Schema registry initialized", extra={
            "schemas_path": str(self.schemas_path),
            "schemas_count": len(self._schemas)
        })
    
    def _load_builtin_schemas(self) -> None:
        """Load built-in schemas."""
        builtin_schemas = {
            "ticks_v1": SchemaDefinition(
                id="ticks_v1",
                version="1.0.0",
                description="Standard tick data schema",
                fields=[
                    FieldDefinition(
                        name="ts",
                        type="timestamp[ns]",
                        nullable=False,
                        description="Timestamp in nanoseconds"
                    ),
                    FieldDefinition(
                        name="symbol",
                        type="string",
                        nullable=False,
                        description="Trading symbol"
                    ),
                    FieldDefinition(
                        name="price",
                        type="float64",
                        nullable=False,
                        description="Trade price"
                    ),
                    FieldDefinition(
                        name="size",
                        type="int64",
                        nullable=False,
                        description="Trade size"
                    ),
                    FieldDefinition(
                        name="side",
                        type="string",
                        nullable=True,
                        description="Trade side (buy/sell)"
                    ),
                    FieldDefinition(
                        name="exchange",
                        type="string",
                        nullable=True,
                        description="Exchange identifier"
                    ),
                    FieldDefinition(
                        name="source_id",
                        type="string",
                        nullable=False,
                        description="Data source identifier"
                    ),
                    FieldDefinition(
                        name="ingest_ts",
                        type="timestamp[ns]",
                        nullable=False,
                        description="Ingestion timestamp"
                    )
                ],
                partition_by=["symbol", "dt"],
                sort_by=["ts"],
                metadata={
                    "compression": "zstd",
                    "compression_level": 5,
                    "batch_size": 16384
                }
            ),
            "alt_nvd_v1": SchemaDefinition(
                id="alt_nvd_v1",
                version="1.0.0",
                description="Alternative data schema for news/sentiment",
                fields=[
                    FieldDefinition(
                        name="ts",
                        type="timestamp[ns]",
                        nullable=False,
                        description="Event timestamp"
                    ),
                    FieldDefinition(
                        name="symbol",
                        type="string",
                        nullable=False,
                        description="Related symbol"
                    ),
                    FieldDefinition(
                        name="event_type",
                        type="string",
                        nullable=False,
                        description="Event type (news, sentiment, etc.)"
                    ),
                    FieldDefinition(
                        name="content",
                        type="string",
                        nullable=True,
                        description="Event content"
                    ),
                    FieldDefinition(
                        name="score",
                        type="float64",
                        nullable=True,
                        description="Sentiment score (-1 to 1)"
                    ),
                    FieldDefinition(
                        name="source",
                        type="string",
                        nullable=True,
                        description="Data source"
                    ),
                    FieldDefinition(
                        name="source_id",
                        type="string",
                        nullable=False,
                        description="Data source identifier"
                    ),
                    FieldDefinition(
                        name="ingest_ts",
                        type="timestamp[ns]",
                        nullable=False,
                        description="Ingestion timestamp"
                    )
                ],
                partition_by=["symbol", "dt"],
                sort_by=["ts"],
                metadata={
                    "compression": "zstd",
                    "compression_level": 3,
                    "batch_size": 8192
                }
            )
        }
        
        for schema_id, schema in builtin_schemas.items():
            self._schemas[schema_id] = schema
            self._save_schema(schema)
    
    def register_schema(self, schema: SchemaDefinition) -> None:
        """
        Register a new schema.
        
        Args:
            schema: Schema definition to register
        """
        self._schemas[schema.id] = schema
        self._save_schema(schema)
        
        logger.info("Schema registered", extra={
            "schema_id": schema.id,
            "version": schema.version,
            "fields_count": len(schema.fields)
        })
    
    def get_schema(self, schema_id: str) -> SchemaDefinition:
        """
        Get schema by ID.
        
        Args:
            schema_id: Schema identifier
            
        Returns:
            Schema definition
            
        Raises:
            KeyError: If schema not found
        """
        if schema_id not in self._schemas:
            # Try to load from file
            schema_file = self.schemas_path / f"{schema_id}.json"
            if schema_file.exists():
                schema = self._load_schema_from_file(schema_file)
                self._schemas[schema_id] = schema
            else:
                raise KeyError(f"Schema '{schema_id}' not found")
        
        return self._schemas[schema_id]
    
    def list_schemas(self) -> List[str]:
        """List all available schema IDs."""
        return list(self._schemas.keys())
    
    def to_arrow_schema(self, schema_id: str) -> pa.Schema:
        """
        Convert schema definition to Arrow schema.
        
        Args:
            schema_id: Schema identifier
            
        Returns:
            Arrow schema
        """
        schema_def = self.get_schema(schema_id)
        
        fields = []
        for field_def in schema_def.fields:
            # Convert type string to Arrow type
            arrow_type = self._parse_arrow_type(field_def.type)
            
            field = pa.field(
                name=field_def.name,
                type=arrow_type,
                nullable=field_def.nullable,
                metadata={
                    "description": field_def.description or "",
                    "constraints": json.dumps(field_def.constraints or {})
                }
            )
            fields.append(field)
        
        return pa.schema(fields, metadata={
            "schema_id": schema_def.id,
            "version": schema_def.version,
            "description": schema_def.description or "",
            "partition_by": json.dumps(schema_def.partition_by or []),
            "sort_by": json.dumps(schema_def.sort_by or [])
        })
    
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
            # Simple struct parsing - could be enhanced
            return pa.struct([])
        
        raise ValueError(f"Unsupported Arrow type: {type_str}")
    
    def _save_schema(self, schema: SchemaDefinition) -> None:
        """Save schema to file."""
        schema_file = self.schemas_path / f"{schema.id}.json"
        with open(schema_file, "w") as f:
            json.dump(schema.model_dump(), f, indent=2)
    
    def _load_schema_from_file(self, schema_file: Path) -> SchemaDefinition:
        """Load schema from file."""
        with open(schema_file, "r") as f:
            data = json.load(f)
        return SchemaDefinition(**data)
    
    def validate_schema_compatibility(
        self,
        schema_id: str,
        table: pa.Table
    ) -> Dict[str, Any]:
        """
        Validate that a table is compatible with a schema.
        
        Args:
            schema_id: Schema identifier
            table: Arrow table to validate
            
        Returns:
            Validation results
        """
        schema_def = self.get_schema(schema_id)
        arrow_schema = self.to_arrow_schema(schema_id)
        
        results = {
            "compatible": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        schema_fields = {f.name for f in arrow_schema}
        table_fields = set(table.column_names)
        
        missing_fields = schema_fields - table_fields
        extra_fields = table_fields - schema_fields
        
        if missing_fields:
            results["compatible"] = False
            results["errors"].append(f"Missing required fields: {missing_fields}")
        
        if extra_fields:
            results["warnings"].append(f"Extra fields in table: {extra_fields}")
        
        # Check field types for common fields
        for field in arrow_schema:
            if field.name in table.column_names:
                table_field = table.schema.field(field.name)
                if not field.type.equals(table_field.type):
                    results["warnings"].append(
                        f"Type mismatch for field '{field.name}': "
                        f"expected {field.type}, got {table_field.type}"
                    )
        
        return results 