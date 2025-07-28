#!/usr/bin/env python3
"""
Basic usage example for Dataset Cleaner + Latency Tick-Store
"""

import pandas as pd
import pyarrow as pa
import duckdb
import numpy as np
from pathlib import Path
import time

def create_sample_data():
    """Create sample tick data."""
    print("Creating sample tick data...")
    
    # Generate sample data
    np.random.seed(42)
    n_rows = 10000
    
    timestamps = pd.date_range('2025-01-27 09:30:00', periods=n_rows, freq='100ms')
    symbols = ['ES', 'NQ', 'YM'] * (n_rows // 3 + 1)
    symbols = symbols[:n_rows]
    
    data = {
        'timestamp': timestamps,
        'symbol': symbols,
        'price': np.random.normal(4500, 50, n_rows),
        'size': np.random.randint(1, 1000, n_rows),
        'side': np.random.choice(['buy', 'sell'], n_rows),
        'exchange': ['CME'] * n_rows
    }
    
    df = pd.DataFrame(data)
    return df

def demonstrate_pandas_processing(df):
    """Demonstrate Pandas data processing."""
    print("\n=== Pandas Processing ===")
    start_time = time.time()
    
    # Basic filtering
    es_data = df[df['symbol'] == 'ES']
    print(f"ES trades: {len(es_data)} rows")
    
    # Aggregations
    volume_by_symbol = df.groupby('symbol')['size'].sum()
    print(f"Volume by symbol:\n{volume_by_symbol}")
    
    # Time-based analysis
    df['hour'] = df['timestamp'].dt.hour
    hourly_volume = df.groupby('hour')['size'].sum()
    print(f"Hourly volume:\n{hourly_volume}")
    
    processing_time = time.time() - start_time
    print(f"Pandas processing time: {processing_time:.3f} seconds")
    return es_data

def demonstrate_pyarrow_processing(df):
    """Demonstrate PyArrow data processing."""
    print("\n=== PyArrow Processing ===")
    start_time = time.time()
    
    # Convert to Arrow table
    table = pa.Table.from_pandas(df)
    print(f"Arrow table: {table.num_rows} rows, {table.num_columns} columns")
    
    # Arrow operations
    price_array = table.column('price')
    # Use compute functions for ChunkedArray
    import pyarrow.compute as pc
    min_price = pc.min(price_array).as_py()
    max_price = pc.max(price_array).as_py()
    print(f"Price statistics: min={min_price:.2f}, max={max_price:.2f}")
    
    # Convert back to pandas
    df_arrow = table.to_pandas()
    
    processing_time = time.time() - start_time
    print(f"PyArrow processing time: {processing_time:.3f} seconds")
    return table

def demonstrate_duckdb_processing(df):
    """Demonstrate DuckDB data processing."""
    print("\n=== DuckDB Processing ===")
    start_time = time.time()
    
    # Connect to in-memory database
    con = duckdb.connect(':memory:')
    
    # Create table from DataFrame
    con.execute("CREATE TABLE ticks AS SELECT * FROM df")
    
    # Complex queries
    result = con.execute("""
        SELECT 
            symbol,
            COUNT(*) as trade_count,
            AVG(price) as avg_price,
            SUM(size) as total_volume,
            MIN(price) as min_price,
            MAX(price) as max_price
        FROM ticks 
        GROUP BY symbol
        ORDER BY total_volume DESC
    """).fetchdf()
    
    print("Symbol statistics:")
    print(result)
    
    # Time-based analysis
    time_result = con.execute("""
        SELECT 
            EXTRACT(hour FROM timestamp) as hour,
            COUNT(*) as trades,
            SUM(size) as volume
        FROM ticks 
        GROUP BY EXTRACT(hour FROM timestamp)
        ORDER BY hour
    """).fetchdf()
    
    print("\nHourly statistics:")
    print(time_result)
    
    processing_time = time.time() - start_time
    print(f"DuckDB processing time: {processing_time:.3f} seconds")
    
    con.close()
    return result

def demonstrate_data_validation(df):
    """Demonstrate data validation."""
    print("\n=== Data Validation ===")
    
    # Basic validation
    print("Data shape:", df.shape)
    print("Data types:")
    print(df.dtypes)
    
    # Check for missing values
    missing_values = df.isnull().sum()
    print("\nMissing values:")
    print(missing_values)
    
    # Value range checks
    print(f"\nPrice range: {df['price'].min():.2f} - {df['price'].max():.2f}")
    print(f"Size range: {df['size'].min()} - {df['size'].max()}")
    
    # Symbol distribution
    symbol_counts = df['symbol'].value_counts()
    print(f"\nSymbol distribution:\n{symbol_counts}")
    
    return True

def save_sample_data(df):
    """Save sample data to files."""
    print("\n=== Saving Sample Data ===")
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Save as CSV
    csv_path = data_dir / "sample_ticks.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")
    
    # Save as Parquet
    parquet_path = data_dir / "sample_ticks.parquet"
    df.to_parquet(parquet_path, index=False)
    print(f"Saved Parquet: {parquet_path}")
    
    # Save as Arrow
    arrow_path = data_dir / "sample_ticks.arrow"
    table = pa.Table.from_pandas(df)
    with pa.ipc.RecordBatchFileWriter(arrow_path, table.schema) as writer:
        writer.write_table(table)
    print(f"Saved Arrow: {arrow_path}")
    
    return csv_path, parquet_path, arrow_path

def main():
    """Main demonstration function."""
    print("🚀 Dataset Cleaner + Latency Tick-Store - Basic Usage Example")
    print("=" * 70)
    
    # Create sample data
    df = create_sample_data()
    print(f"Created {len(df)} sample records")
    
    # Demonstrate different processing methods
    demonstrate_pandas_processing(df)
    demonstrate_pyarrow_processing(df)
    demonstrate_duckdb_processing(df)
    demonstrate_data_validation(df)
    
    # Save data
    csv_path, parquet_path, arrow_path = save_sample_data(df)
    
    print("\n" + "=" * 70)
    print("✅ Basic usage example completed successfully!")
    print("\nGenerated files:")
    print(f"  - CSV: {csv_path}")
    print(f"  - Parquet: {parquet_path}")
    print(f"  - Arrow: {arrow_path}")
    
    print("\nNext steps:")
    print("1. Explore the generated data files")
    print("2. Try the Rust components: cd src/rust && cargo run")
    print("3. Run performance benchmarks")
    print("4. Check out the CLI: python -m tickdb --help")

if __name__ == "__main__":
    main() 