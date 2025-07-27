"""
Basic usage example for TickDB.

This example demonstrates:
1. Loading data from a CSV file
2. Appending DataFrame data
3. Querying data with filters
4. Basic system operations
"""

import pandas as pd
from pathlib import Path

from tickdb import TickDB, TickDBConfig


def main():
    """Run basic usage example."""
    print("🚀 TickDB Basic Usage Example")
    print("=" * 50)
    
    # Initialize TickDB with custom configuration
    config = TickDBConfig(
        data_path=Path("./example_data"),
        quarantine_path=Path("./example_quarantine"),
        batch_size=8192,
        enable_metrics=True
    )
    
    tickdb = TickDB(config)
    
    print("✅ TickDB initialized successfully")
    
    # 1. Load data from CSV file
    print("\n📁 Loading data from CSV file...")
    csv_file = Path("examples/sample_ticks.csv")
    
    if csv_file.exists():
        result = tickdb.load_raw(
            source_id="example_cme",
            path=csv_file,
            schema_id="ticks_v1"
        )
        
        print(f"   Rows processed: {result['rows_processed']}")
        print(f"   Rows failed: {result['rows_failed']}")
        print(f"   Files created: {len(result['files_created'])}")
    else:
        print("   ⚠️  Sample CSV file not found, creating test data...")
        
        # Create test data
        df = pd.DataFrame({
            "ts": pd.date_range("2025-01-27T09:30:00", periods=100, freq="100ms"),
            "symbol": ["ES"] * 50 + ["NQ"] * 50,
            "price": [4500 + i * 0.25 for i in range(100)],
            "size": [100 + i * 2 for i in range(100)],
            "side": ["buy" if i % 2 == 0 else "sell" for i in range(100)],
            "exchange": ["CME"] * 100
        })
        
        result = tickdb.append(df, "ticks_v1", "example_generated")
        print(f"   Rows processed: {result['rows_processed']}")
        print(f"   Rows failed: {result['rows_failed']}")
    
    # 2. List available schemas
    print("\n📋 Available schemas:")
    schemas = tickdb.list_schemas()
    for schema_id in schemas:
        schema = tickdb.get_schema(schema_id)
        print(f"   - {schema_id}: {schema['description']}")
    
    # 3. Query data
    print("\n🔍 Querying data...")
    
    # Query ES symbols
    es_data = tickdb.read(
        symbol="ES",
        fields=["ts", "symbol", "price", "size", "side"]
    )
    print(f"   ES data: {len(es_data)} rows")
    
    # Query with time range
    time_range_data = tickdb.read(
        symbol="ES",
        ts_start="2025-01-27T09:30:00Z",
        ts_end="2025-01-27T09:30:01Z",
        fields=["ts", "price", "size"]
    )
    print(f"   ES data (time range): {len(time_range_data)} rows")
    
    # Query NQ symbols
    nq_data = tickdb.read(
        symbol="NQ",
        fields=["ts", "symbol", "price", "size"]
    )
    print(f"   NQ data: {len(nq_data)} rows")
    
    # 4. Show sample data
    if len(es_data) > 0:
        print("\n📊 Sample ES data:")
        df = es_data.to_pandas()
        print(df.head().to_string(index=False))
    
    # 5. List symbols
    print("\n📈 Available symbols:")
    symbols = tickdb.reader.list_symbols("ticks_v1")
    for symbol in symbols:
        print(f"   - {symbol}")
    
    # 6. Get metadata
    print("\n📊 Data lake metadata:")
    metadata = tickdb.reader.get_metadata("ticks_v1")
    print(f"   Total files: {metadata['total_files']}")
    print(f"   Total rows: {metadata['total_rows']}")
    
    date_range = tickdb.reader.get_date_range(schema_id="ticks_v1")
    print(f"   Date range: {date_range['min_ts']} to {date_range['max_ts']}")
    
    # 7. Health check
    print("\n🏥 System health:")
    health = tickdb.health_check()
    print(f"   Status: {health['status']}")
    
    # 8. Show metrics
    print("\n📈 System metrics:")
    metrics = tickdb.get_metrics()
    if metrics:
        aggregates = metrics.get("aggregates", {})
        print(f"   Total ingest bytes: {aggregates.get('total_ingest_bytes', 0):,}")
        print(f"   Total ingest rows: {aggregates.get('total_ingest_rows', 0):,}")
        print(f"   Total queries: {aggregates.get('total_queries', 0)}")
        print(f"   Avg throughput: {aggregates.get('avg_ingest_throughput_mbps', 0):.2f} MB/s")
    else:
        print("   No metrics available")
    
    print("\n✅ Example completed successfully!")
    print("\n💡 Try these commands:")
    print("   tickdb query --symbol ES --limit 10")
    print("   tickdb list-symbols")
    print("   tickdb metadata")
    print("   tickdb health")


if __name__ == "__main__":
    main() 