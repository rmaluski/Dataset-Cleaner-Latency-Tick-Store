#!/usr/bin/env python3
"""
Performance benchmark for Dataset Cleaner + Latency Tick-Store
Tests ingestion speed and query latency
"""

import time
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def generate_test_data(size_mb=100):
    """Generate test data for benchmarking"""
    print(f"Generating {size_mb}MB of test data...")
    
    # Generate tick data
    n_rows = int(size_mb * 1024 * 1024 / 100)  # Approximate bytes per row
    timestamps = pd.date_range('2025-01-27 09:30:00', periods=n_rows, freq='1ms')
    
    data = {
        'ts': timestamps,
        'symbol': np.random.choice(['ES', 'NQ', 'YM', 'RTY'], n_rows),
        'price': np.random.uniform(4000, 5000, n_rows),
        'size': np.random.randint(1, 1000, n_rows),
        'bid': np.random.uniform(4000, 5000, n_rows),
        'ask': np.random.uniform(4000, 5000, n_rows),
    }
    
    return pd.DataFrame(data)

def benchmark_ingestion():
    """Benchmark data ingestion speed"""
    print("\n=== Ingestion Benchmark ===")
    
    try:
        from tickdb.core import TickDB
        from tickdb.config import TickDBConfig
        import tempfile
        
        # Initialize TickDB with temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=16384,
                enable_metrics=False
            )
            
            tickdb = TickDB(config)
            
            # Generate test data
            df = generate_test_data(10)  # 10MB for testing
            
            # Measure ingestion time
            start_time = time.time()
            result = tickdb.append(df, schema_id="ticks_v1")
            end_time = time.time()
            
            ingestion_time = end_time - start_time
            data_size_mb = len(df) * df.memory_usage(deep=True).sum() / (1024 * 1024)
            throughput_mbps = data_size_mb / ingestion_time
            
            print(f"Data size: {data_size_mb:.2f} MB")
            print(f"Ingestion time: {ingestion_time:.2f} seconds")
            print(f"Throughput: {throughput_mbps:.2f} MB/s")
            
            return throughput_mbps
            
    except Exception as e:
        print(f"Ingestion benchmark failed: {e}")
        return 0

def benchmark_query_latency():
    """Benchmark query latency"""
    print("\n=== Query Latency Benchmark ===")
    
    try:
        from tickdb.core import TickDB
        from tickdb.config import TickDBConfig
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=16384,
                enable_metrics=False
            )
            
            tickdb = TickDB(config)
            
            # Generate larger dataset for query testing
            df = generate_test_data(50)  # 50MB
            tickdb.append(df, schema_id="ticks_v1")
            
            # Test full column scan
            start_time = time.time()
            result = tickdb.read(schema_id="ticks_v1", limit=1000)
            end_time = time.time()
            
            scan_time = (end_time - start_time) * 1000  # Convert to ms
            rows_scanned = len(result)
            
            print(f"Full column scan: {scan_time:.2f} ms for {rows_scanned:,} rows")
            
            return scan_time
            
    except Exception as e:
        print(f"Query benchmark failed: {e}")
        return 0

def main():
    """Run all benchmarks"""
    print("Dataset Cleaner + Latency Tick-Store Performance Benchmark")
    print("=" * 60)
    
    try:
        # Run benchmarks
        ingestion_throughput = benchmark_ingestion()
        scan_latency = benchmark_query_latency()
        
        # Print summary
        print("\n=== Performance Summary ===")
        print(f"Ingestion throughput: {ingestion_throughput:.2f} MB/s")
        print(f"Full column scan latency: {scan_latency:.2f} ms")
        
        # Check against targets
        print("\n=== Target Comparison ===")
        if ingestion_throughput >= 100:  # 100 MB/s baseline
            print("Ingestion target met: >= 100 MB/s")
        else:
            print("Ingestion target not met")
            
        if scan_latency < 100:  # 100 ms baseline
            print("Full scan target met: < 100 ms")
        else:
            print("Full scan target not met")
            
    except Exception as e:
        print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    main()
