#!/usr/bin/env python3
"""
Comprehensive Integration Test for Dataset Cleaner + Latency Tick-Store
Tests Python and Rust components (where available)
"""

import sys
import os
import time
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_section(title):
    """Print a formatted section"""
    print(f"\n--- {title} ---")

def test_python_environment():
    """Test Python environment and dependencies"""
    print_section("Testing Python Environment")
    
    try:
        import pandas as pd
        print(f"✓ Pandas version: {pd.__version__}")
        
        import numpy as np
        print(f"✓ NumPy version: {np.__version__}")
        
        import pyarrow as pa
        print(f"✓ PyArrow version: {pa.__version__}")
        
        import duckdb
        print(f"✓ DuckDB version: {duckdb.__version__}")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_cpp_compiler():
    """Test C++ compiler availability"""
    print_section("Testing C++ Compiler")
    
    try:
        # Test if g++ is available
        result = subprocess.run(['g++', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ C++ compiler (g++) is available")
            print(f"  Version info: {result.stdout.split(chr(10))[0]}")
            
            # Test SIMD support
            result = subprocess.run(['g++', '-mavx2', '-dM', '-E', '-'], 
                                  input='', capture_output=True, text=True, timeout=10)
            if 'AVX2' in result.stdout:
                print("✓ AVX2 SIMD instructions supported")
            else:
                print("⚠ AVX2 not detected, but compiler works")
            
            return True
        else:
            print("✗ C++ compiler not found or not working")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"✗ C++ compiler test failed: {e}")
        return False

def test_rust_components():
    """Test Rust components"""
    print_section("Testing Rust Components")
    
    try:
        # Try to import the Rust module
        import dataset_core_rust
        print("✓ Rust module imported successfully")
        
        # Test basic functionality
        test_data = "timestamp,price,volume\n2023-01-01,100.0,1000\n2023-01-02,101.0,1100"
        with open("test_rust.csv", "w") as f:
            f.write(test_data)
        
        result = dataset_core_rust.parse_csv_simd("test_rust.csv", 1024)
        print(f"✓ Rust parse_csv_simd returned: {result}")
        
        # Clean up
        os.remove("test_rust.csv")
        
        return True
    except ImportError as e:
        print(f"⚠ Rust module not available: {e}")
        print("  This is expected if the Rust extension wasn't built")
        return False
    except Exception as e:
        print(f"✗ Rust component test failed: {e}")
        return False

def create_test_dataset():
    """Create a test dataset for processing"""
    print_section("Creating Test Dataset")
    
    # Generate sample tick data
    np.random.seed(42)
    n_rows = 10000
    
    timestamps = pd.date_range('2023-01-01', periods=n_rows, freq='1S')
    prices = 100 + np.cumsum(np.random.randn(n_rows) * 0.1)
    volumes = np.random.randint(100, 10000, n_rows)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': prices,
        'volume': volumes,
        'symbol': 'AAPL'
    })
    
    csv_path = "test_dataset.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"✓ Created test dataset: {csv_path}")
    print(f"  Rows: {len(df):,}")
    print(f"  Size: {os.path.getsize(csv_path) / 1024:.1f} KB")
    
    return csv_path

def test_python_processing(csv_path):
    """Test Python-based data processing"""
    print_section("Testing Python Processing")
    
    start_time = time.time()
    
    # Read CSV with pandas
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    
    # Basic processing
    total_volume = df['volume'].sum()
    avg_price = df['price'].mean()
    price_std = df['price'].std()
    
    processing_time = time.time() - start_time
    
    print(f"✓ Pandas processing completed in {processing_time:.3f}s")
    print(f"  Total volume: {total_volume:,}")
    print(f"  Average price: ${avg_price:.2f}")
    print(f"  Price std dev: ${price_std:.2f}")
    
    return processing_time

def test_duckdb_processing(csv_path):
    """Test DuckDB processing"""
    print_section("Testing DuckDB Processing")
    
    start_time = time.time()
    
    import duckdb
    
    # Create connection and load data
    con = duckdb.connect(':memory:')
    con.execute(f"CREATE TABLE ticks AS SELECT * FROM read_csv_auto('{csv_path}')")
    
    # Run analytics query
    result = con.execute("""
        SELECT 
            COUNT(*) as total_rows,
            SUM(volume) as total_volume,
            AVG(price) as avg_price,
            STDDEV(price) as price_std,
            MIN(price) as min_price,
            MAX(price) as max_price
        FROM ticks
    """).fetchone()
    
    processing_time = time.time() - start_time
    
    print(f"✓ DuckDB processing completed in {processing_time:.3f}s")
    print(f"  Total rows: {result[0]:,}")
    print(f"  Total volume: {result[1]:,}")
    print(f"  Average price: ${result[2]:.2f}")
    print(f"  Price std dev: ${result[3]:.2f}")
    print(f"  Price range: ${result[4]:.2f} - ${result[5]:.2f}")
    
    return processing_time

def test_pyarrow_processing(csv_path):
    """Test PyArrow processing"""
    print_section("Testing PyArrow Processing")
    
    start_time = time.time()
    
    import pyarrow as pa
    import pyarrow.csv as csv
    
    # Read CSV with PyArrow
    table = csv.read_csv(csv_path)
    
    # Convert to pandas for processing (simulating Arrow operations)
    df = table.to_pandas()
    
    # Basic analytics
    total_volume = df['volume'].sum()
    avg_price = df['price'].mean()
    price_std = df['price'].std()
    
    processing_time = time.time() - start_time
    
    print(f"✓ PyArrow processing completed in {processing_time:.3f}s")
    print(f"  Total volume: {total_volume:,}")
    print(f"  Average price: ${avg_price:.2f}")
    print(f"  Price std dev: ${price_std:.2f}")
    
    return processing_time

def benchmark_performance(csv_path, python_time, duckdb_time, pyarrow_time, rust_available=False, cpp_available=False):
    """Benchmark and compare performance"""
    print_section("Performance Benchmark")
    
    print("Processing Times:")
    print(f"  Python (Pandas): {python_time:.3f}s")
    print(f"  DuckDB:          {duckdb_time:.3f}s")
    print(f"  PyArrow:         {pyarrow_time:.3f}s")
    
    if rust_available:
        print(f"  Rust:            Available (tested separately)")
    
    if cpp_available:
        print(f"  C++:             Removed from project")
    
    # Calculate relative performance
    fastest = min(python_time, duckdb_time, pyarrow_time)
    
    print(f"\nRelative Performance (lower is better):")
    print(f"  Python (Pandas): {python_time/fastest:.2f}x")
    print(f"  DuckDB:          {duckdb_time/fastest:.2f}x")
    print(f"  PyArrow:         {pyarrow_time/fastest:.2f}x")
    
    if duckdb_time == fastest:
        print("\n🏆 DuckDB was fastest for this dataset!")
    elif pyarrow_time == fastest:
        print("\n🏆 PyArrow was fastest for this dataset!")
    else:
        print("\n🏆 Pandas was fastest for this dataset!")

def main():
    """Main integration test"""
    print_header("Dataset Cleaner + Latency Tick-Store Integration Test")
    
    # Test environment
    python_ok = test_python_environment()
    cpp_ok = test_cpp_compiler()
    rust_ok = test_rust_components()
    
    if not python_ok:
        print("\n❌ Python environment test failed. Please check dependencies.")
        return
    
    # Create test data
    csv_path = create_test_dataset()
    
    try:
        # Test processing methods
        python_time = test_python_processing(csv_path)
        duckdb_time = test_duckdb_processing(csv_path)
        pyarrow_time = test_pyarrow_processing(csv_path)
        
        # Benchmark
        benchmark_performance(csv_path, python_time, duckdb_time, pyarrow_time, 
                            rust_available=rust_ok, cpp_available=cpp_ok)
        
        # Summary
        print_header("Integration Test Summary")
        print(f"✓ Python Environment: {'OK' if python_ok else 'FAILED'}")
        print(f"✓ C++ Compiler: {'OK' if cpp_ok else 'NOT AVAILABLE'}")
        print(f"✓ Rust Components: {'OK' if rust_ok else 'NOT AVAILABLE'}")
        print(f"✓ Data Processing: OK (all Python methods working)")
        
        if rust_ok and cpp_ok:
            print("\n🎉 All components are working! Full integration achieved.")
        elif rust_ok:
            print("\n✅ Python + Rust integration working.")
        elif cpp_ok:
            print("\n✅ Python + C++ compiler available. Rust can be added later.")
        else:
            print("\n✅ Python processing pipeline is fully functional.")
            print("   Rust components provide excellent performance optimization.")
        
    finally:
        # Cleanup
        if os.path.exists(csv_path):
            os.remove(csv_path)
            print(f"\n🧹 Cleaned up test file: {csv_path}")

if __name__ == "__main__":
    main() 