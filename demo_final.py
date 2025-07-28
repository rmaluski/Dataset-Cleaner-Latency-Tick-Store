#!/usr/bin/env python3
"""
Final Demo - Dataset Cleaner + Latency Tick-Store
Showcases the current working capabilities of the project
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from pathlib import Path

def print_banner():
    """Print project banner"""
    print("="*70)
    print("  Dataset Cleaner + Latency Tick-Store - Final Demo")
    print("="*70)
    print("  Status: OPERATIONAL - Python Pipeline Ready")
    print("  Next: Rust/C++ Performance Optimizations")
    print("="*70)

def demo_data_generation():
    """Demonstrate data generation capabilities"""
    print("\n📊 Data Generation Demo")
    print("-" * 40)
    
    # Generate realistic tick data
    np.random.seed(42)
    n_ticks = 50000
    
    # Create timestamp range
    timestamps = pd.date_range('2023-01-01 09:30:00', periods=n_ticks, freq='100ms')
    
    # Generate realistic price movements (random walk with mean reversion)
    base_price = 150.0
    price_changes = np.random.randn(n_ticks) * 0.1
    prices = base_price + np.cumsum(price_changes)
    
    # Generate realistic volumes
    volumes = np.random.randint(100, 5000, n_ticks)
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'symbol': 'AAPL',
        'price': prices,
        'volume': volumes,
        'bid': prices - np.random.uniform(0.01, 0.05, n_ticks),
        'ask': prices + np.random.uniform(0.01, 0.05, n_ticks)
    })
    
    print(f"✓ Generated {n_ticks:,} tick records")
    print(f"✓ Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"✓ Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
    print(f"✓ Total volume: {df['volume'].sum():,}")
    
    return df

def demo_pandas_processing(df):
    """Demonstrate Pandas processing capabilities"""
    print("\n🐼 Pandas Processing Demo")
    print("-" * 40)
    
    start_time = time.time()
    
    # Basic statistics
    stats = {
        'total_ticks': len(df),
        'avg_price': df['price'].mean(),
        'price_std': df['price'].std(),
        'total_volume': df['volume'].sum(),
        'avg_volume': df['volume'].mean(),
        'spread_avg': (df['ask'] - df['bid']).mean()
    }
    
    # Time-based analysis
    df['hour'] = df['timestamp'].dt.hour
    hourly_stats = df.groupby('hour').agg({
        'price': ['mean', 'std'],
        'volume': 'sum'
    }).round(2)
    
    processing_time = time.time() - start_time
    
    print(f"✓ Processing completed in {processing_time:.3f}s")
    print(f"✓ Total ticks: {stats['total_ticks']:,}")
    print(f"✓ Average price: ${stats['avg_price']:.2f}")
    print(f"✓ Price volatility: ${stats['price_std']:.2f}")
    print(f"✓ Total volume: {stats['total_volume']:,}")
    print(f"✓ Average spread: ${stats['spread_avg']:.4f}")
    
    return stats, hourly_stats

def demo_duckdb_processing(df):
    """Demonstrate DuckDB processing capabilities"""
    print("\n🦆 DuckDB Processing Demo")
    print("-" * 40)
    
    import duckdb
    
    start_time = time.time()
    
    # Create connection and load data
    con = duckdb.connect(':memory:')
    con.execute("CREATE TABLE ticks AS SELECT * FROM df")
    
    # Complex SQL analytics
    result = con.execute("""
        SELECT 
            EXTRACT(hour FROM timestamp) as hour,
            COUNT(*) as tick_count,
            AVG(price) as avg_price,
            STDDEV(price) as price_volatility,
            SUM(volume) as total_volume,
            AVG(ask - bid) as avg_spread,
            MIN(price) as min_price,
            MAX(price) as max_price
        FROM ticks 
        GROUP BY EXTRACT(hour FROM timestamp)
        ORDER BY hour
    """).fetchdf()
    
    processing_time = time.time() - start_time
    
    print(f"✓ SQL processing completed in {processing_time:.3f}s")
    print("✓ Hourly statistics:")
    print(result.to_string(index=False))
    
    return result

def demo_pyarrow_processing(df):
    """Demonstrate PyArrow processing capabilities"""
    print("\n🏹 PyArrow Processing Demo")
    print("-" * 40)
    
    import pyarrow as pa
    import pyarrow.compute as pc
    
    start_time = time.time()
    
    # Convert to Arrow table
    table = pa.Table.from_pandas(df)
    
    # Arrow-based computations
    price_array = table.column('price')
    volume_array = table.column('volume')
    
    # Compute statistics using Arrow
    arrow_stats = {
        'avg_price': pc.mean(price_array).as_py(),
        'price_std': pc.stddev(price_array).as_py(),
        'total_volume': pc.sum(volume_array).as_py(),
        'min_price': pc.min(price_array).as_py(),
        'max_price': pc.max(price_array).as_py()
    }
    
    processing_time = time.time() - start_time
    
    print(f"✓ Arrow processing completed in {processing_time:.3f}s")
    print(f"✓ Average price: ${arrow_stats['avg_price']:.2f}")
    print(f"✓ Price volatility: ${arrow_stats['price_std']:.2f}")
    print(f"✓ Total volume: {arrow_stats['total_volume']:,}")
    print(f"✓ Price range: ${arrow_stats['min_price']:.2f} - ${arrow_stats['max_price']:.2f}")
    
    return arrow_stats

def demo_performance_comparison(df):
    """Compare performance of different processing methods"""
    print("\n⚡ Performance Comparison")
    print("-" * 40)
    
    times = {}
    
    # Pandas timing
    start = time.time()
    _ = df.groupby(df['timestamp'].dt.hour)['price'].mean()
    times['Pandas'] = time.time() - start
    
    # DuckDB timing
    start = time.time()
    import duckdb
    con = duckdb.connect(':memory:')
    con.execute("CREATE TABLE ticks AS SELECT * FROM df")
    _ = con.execute("SELECT EXTRACT(hour FROM timestamp) as hour, AVG(price) as avg_price FROM ticks GROUP BY EXTRACT(hour FROM timestamp)").fetchdf()
    times['DuckDB'] = time.time() - start
    
    # PyArrow timing
    start = time.time()
    import pyarrow as pa
    import pyarrow.compute as pc
    table = pa.Table.from_pandas(df)
    _ = pc.mean(table.column('price')).as_py()
    times['PyArrow'] = time.time() - start
    
    # Display results
    fastest = min(times.values())
    print("Processing Times:")
    for method, t in times.items():
        relative = t / fastest
        print(f"  {method:8}: {t:.4f}s ({relative:.2f}x)")
    
    fastest_method = min(times, key=times.get)
    print(f"\n🏆 {fastest_method} was fastest!")

def demo_data_export(df):
    """Demonstrate data export capabilities"""
    print("\n💾 Data Export Demo")
    print("-" * 40)
    
    # Export to different formats
    formats = {
        'CSV': 'demo_ticks.csv',
        'Parquet': 'demo_ticks.parquet',
        'JSON': 'demo_ticks.json'
    }
    
    for format_name, filename in formats.items():
        start_time = time.time()
        
        if format_name == 'CSV':
            df.to_csv(filename, index=False)
        elif format_name == 'Parquet':
            df.to_parquet(filename, index=False)
        elif format_name == 'JSON':
            df.to_json(filename, orient='records', indent=2)
        
        export_time = time.time() - start_time
        file_size = os.path.getsize(filename) / 1024  # KB
        
        print(f"✓ {format_name:8}: {export_time:.3f}s, {file_size:.1f} KB")
    
    # Clean up
    for filename in formats.values():
        if os.path.exists(filename):
            os.remove(filename)

def main():
    """Main demo function"""
    print_banner()
    
    try:
        # Generate sample data
        df = demo_data_generation()
        
        # Demonstrate different processing methods
        pandas_stats, hourly_stats = demo_pandas_processing(df)
        duckdb_result = demo_duckdb_processing(df)
        arrow_stats = demo_pyarrow_processing(df)
        
        # Performance comparison
        demo_performance_comparison(df)
        
        # Data export
        demo_data_export(df)
        
        # Summary
        print("\n" + "="*70)
        print("🎉 Demo Completed Successfully!")
        print("="*70)
        print("✅ All Python processing methods working")
        print("✅ Performance benchmarking functional")
        print("✅ Data export capabilities ready")
        print("✅ Ready for Rust/C++ optimizations")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 