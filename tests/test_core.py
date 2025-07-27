"""
Unit tests for TickDB core functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pyarrow as pa
import pytest

from tickdb.core import TickDB, TickDBConfig


class TestTickDBConfig:
    """Test TickDBConfig class."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = TickDBConfig()
        
        assert config.data_path == Path("./data")
        assert config.quarantine_path == Path("./quarantine")
        assert config.batch_size == 16384
        assert config.compression == "zstd"
        assert config.compression_level == 5
        assert config.enable_metrics is True
        assert config.enable_logging is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TickDBConfig(
            data_path=Path("/custom/data"),
            quarantine_path=Path("/custom/quarantine"),
            batch_size=8192,
            compression="snappy",
            compression_level=3,
            enable_metrics=False,
            enable_logging=False
        )
        
        assert config.data_path == Path("/custom/data")
        assert config.quarantine_path == Path("/custom/quarantine")
        assert config.batch_size == 8192
        assert config.compression == "snappy"
        assert config.compression_level == 3
        assert config.enable_metrics is False
        assert config.enable_logging is False


class TestTickDB:
    """Test TickDB class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def tickdb(self, temp_dir):
        """Create TickDB instance for tests."""
        config = TickDBConfig(
            data_path=temp_dir / "data",
            quarantine_path=temp_dir / "quarantine",
            enable_metrics=False
        )
        return TickDB(config)
    
    def test_initialization(self, temp_dir):
        """Test TickDB initialization."""
        config = TickDBConfig(
            data_path=temp_dir / "data",
            quarantine_path=temp_dir / "quarantine"
        )
        
        tickdb = TickDB(config)
        
        assert tickdb.config == config
        assert tickdb.config.data_path.exists()
        assert tickdb.config.quarantine_path.exists()
        assert tickdb.schema_registry is not None
        assert tickdb.loader is not None
        assert tickdb.reader is not None
        assert tickdb.validator is not None
        assert tickdb.metrics is None  # Disabled in config
    
    def test_list_schemas(self, tickdb):
        """Test listing schemas."""
        schemas = tickdb.list_schemas()
        
        assert isinstance(schemas, list)
        assert "ticks_v1" in schemas
        assert "alt_nvd_v1" in schemas
    
    def test_get_schema(self, tickdb):
        """Test getting schema."""
        schema = tickdb.get_schema("ticks_v1")
        
        assert schema["id"] == "ticks_v1"
        assert schema["version"] == "1.0.0"
        assert "fields" in schema
        assert len(schema["fields"]) > 0
    
    def test_get_schema_not_found(self, tickdb):
        """Test getting non-existent schema."""
        with pytest.raises(KeyError):
            tickdb.get_schema("non_existent_schema")
    
    def test_health_check(self, tickdb):
        """Test health check."""
        health = tickdb.health_check()
        
        assert "status" in health
        assert "components" in health
        assert health["status"] == "healthy"
    
    def test_append_dataframe(self, tickdb):
        """Test appending DataFrame."""
        # Create test data
        df = pd.DataFrame({
            "ts": pd.date_range("2025-01-01", periods=10, freq="1s"),
            "symbol": ["ES"] * 10,
            "price": [100.0 + i for i in range(10)],
            "size": [100] * 10
        })
        
        result = tickdb.append(df, "ticks_v1", "test_source")
        
        assert "rows_processed" in result
        assert "rows_failed" in result
        assert "files_created" in result
    
    def test_read_data(self, tickdb):
        """Test reading data."""
        # First, add some data
        df = pd.DataFrame({
            "ts": pd.date_range("2025-01-01", periods=10, freq="1s"),
            "symbol": ["ES"] * 10,
            "price": [100.0 + i for i in range(10)],
            "size": [100] * 10
        })
        
        tickdb.append(df, "ticks_v1", "test_source")
        
        # Now read the data
        result = tickdb.read(
            symbol="ES",
            ts_start="2025-01-01T00:00:00Z",
            ts_end="2025-01-01T00:00:10Z",
            fields=["ts", "symbol", "price"]
        )
        
        assert isinstance(result, pa.Table)
        assert len(result) > 0
    
    def test_get_metrics_disabled(self, tickdb):
        """Test getting metrics when disabled."""
        metrics = tickdb.get_metrics()
        assert metrics == {}
    
    @patch("tickdb.core.MetricsCollector")
    def test_get_metrics_enabled(self, mock_metrics_collector, temp_dir):
        """Test getting metrics when enabled."""
        config = TickDBConfig(
            data_path=temp_dir / "data",
            quarantine_path=temp_dir / "quarantine",
            enable_metrics=True
        )
        
        mock_metrics = Mock()
        mock_metrics.get_metrics.return_value = {"test": "metrics"}
        mock_metrics_collector.return_value = mock_metrics
        
        tickdb = TickDB(config)
        metrics = tickdb.get_metrics()
        
        assert metrics == {"test": "metrics"}
        mock_metrics.get_metrics.assert_called_once()


class TestTickDBIntegration:
    """Integration tests for TickDB."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def tickdb(self, temp_dir):
        """Create TickDB instance for integration tests."""
        config = TickDBConfig(
            data_path=temp_dir / "data",
            quarantine_path=temp_dir / "quarantine",
            enable_metrics=False
        )
        return TickDB(config)
    
    def test_full_workflow(self, tickdb):
        """Test complete workflow: load, validate, store, query."""
        # Create test data
        df = pd.DataFrame({
            "ts": pd.date_range("2025-01-01", periods=100, freq="1s"),
            "symbol": ["ES"] * 50 + ["NQ"] * 50,
            "price": [100.0 + i * 0.1 for i in range(100)],
            "size": [100 + i for i in range(100)]
        })
        
        # Append data
        append_result = tickdb.append(df, "ticks_v1", "test_source")
        assert append_result["rows_processed"] == 100
        assert append_result["rows_failed"] == 0
        
        # Query data
        result = tickdb.read(
            symbol="ES",
            fields=["ts", "symbol", "price", "size"]
        )
        
        assert isinstance(result, pa.Table)
        assert len(result) == 50  # Only ES symbols
        
        # Query with time range
        result = tickdb.read(
            symbol="ES",
            ts_start="2025-01-01T00:00:00Z",
            ts_end="2025-01-01T00:00:30Z",
            fields=["ts", "price"]
        )
        
        assert len(result) <= 30  # Should be 30 or fewer rows
    
    def test_error_handling(self, tickdb):
        """Test error handling with invalid data."""
        # Create invalid data (negative prices)
        df = pd.DataFrame({
            "ts": pd.date_range("2025-01-01", periods=10, freq="1s"),
            "symbol": ["ES"] * 10,
            "price": [-100.0] * 10,  # Invalid negative prices
            "size": [100] * 10
        })
        
        result = tickdb.append(df, "ticks_v1", "test_source")
        
        # Should have failed rows due to validation
        assert result["rows_failed"] > 0
    
    def test_schema_validation(self, tickdb):
        """Test schema validation."""
        # Create data with missing required fields
        df = pd.DataFrame({
            "ts": pd.date_range("2025-01-01", periods=10, freq="1s"),
            "price": [100.0] * 10,
            "size": [100] * 10
            # Missing 'symbol' field
        })
        
        result = tickdb.append(df, "ticks_v1", "test_source")
        
        # Should fail due to missing required field
        assert result["rows_failed"] > 0 