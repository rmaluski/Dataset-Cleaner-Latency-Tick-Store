"""
High-throughput data lake for financial tick data.

This package provides a universal, high-throughput data-lake that every later module depends on.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core import TickDB
from .config import TickDBConfig
from .schemas import SchemaRegistry
from .loader import DataLoader
from .reader import DataReader
from .validation import DataValidator
from .metrics import MetricsCollector

__all__ = [
    "TickDB",
    "TickDBConfig",
    "SchemaRegistry", 
    "DataLoader",
    "DataReader",
    "DataValidator",
    "MetricsCollector",
] 