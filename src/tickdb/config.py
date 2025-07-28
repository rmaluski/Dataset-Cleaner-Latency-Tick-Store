"""
Configuration module for TickDB.
"""

from pathlib import Path
from pydantic import BaseModel, Field


class TickDBConfig(BaseModel):
    """Configuration for TickDB."""
    
    data_path: Path = Field(default=Path("./data"), description="Base path for data storage")
    quarantine_path: Path = Field(default=Path("./quarantine"), description="Path for failed rows")
    batch_size: int = Field(default=16384, description="Batch size for processing")
    compression: str = Field(default="zstd", description="Compression algorithm")
    compression_level: int = Field(default=5, description="Compression level")
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    enable_logging: bool = Field(default=True, description="Enable structured logging") 