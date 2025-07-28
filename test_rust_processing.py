#!/usr/bin/env python3
"""
Test script to use Rust components for real data processing.
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from pathlib import Path

# Add the Rust module to Python path
sys.path.insert(0, os.path.join('src', 'rust', 'target', 'release'))

def create_test_csv():
    """Create a test CSV file for processing."""
    print("Creating test CSV data...")
    
    # Generate realistic tick data
    np.random.seed(42)
    n_rows = 50000  # 50K rows for testing
    
    timestamps = pd.date_range('2025-01-27 09:30:00', periods=n_rows, freq='10ms')
    symbols = ['ES', 'NQ', 'YM', 'RTY', 'CL'] * (n_rows // 5 + 1)
    symbols = symbols[:n_rows]
    
    data = {
        'timestamp': timestamps,
        'symbol': symbols,
        'price': np.random.normal(4500, 50, n_rows),
        'size': np.random.randint(1, 1000, n_rows),
        'side': np.random.choice(['buy', 'sell'], n_rows),
        'exchange': ['CME'] * n_rows,
        'sequence': range(n_rows)
    }
    
    df = pd.DataFrame(data)
    
    # Create test directory
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # Save as CSV
    csv_path = test_dir / "test_ticks.csv"
    df.to_csv(csv_path, index=False)
    print(f"Created test CSV: {csv_path} ({len(df)} rows)")
    
    return csv_path, df

def test_python_processing(csv_path):
    """Test Python-based CSV processing."""
    print("\n=== Python CSV Processing ===")
    start_time = time.time()
    
    # Read CSV with pandas
    df = pd.read_csv(csv_path)
    read_time = time.time() - start_time
    
    print(f"Read {len(df)} rows in {read_time:.3f} seconds")
    print(f"Throughput: {len(df) / read_time:.0f} rows/second")
    
    # Basic processing
    process_start = time.time()
    
    # Filter by symbol
    es_data = df[df['symbol'] == 'ES']
    
    # Calculate statistics
    stats = df.groupby('symbol').agg({
        'price': ['mean', 'std', 'min', 'max'],
        'size': ['sum', 'mean']
    }).round(2)
    
    process_time = time.time() - process_start
    print(f"Processing time: {process_time:.3f} seconds")
    print(f"ES trades: {len(es_data)} rows")
    print(f"Symbol statistics:\n{stats}")
    
    return df, read_time + process_time

def test_rust_processing(csv_path):
    """Test Rust-based CSV processing."""
    print("\n=== Rust CSV Processing ===")
    
    try:
        # Import the Rust module
        import dataset_core_rust
        
        start_time = time.time()
        
        # Use the Rust SIMD parser
        result = dataset_core_rust.parse_csv_simd(csv_path, 8192)
        
        processing_time = time.time() - start_time
        
        print(f"Rust processing result: {result}")
        print(f"Processing time: {processing_time:.3f} seconds")
        
        return result, processing_time
        
    except ImportError as e:
        print(f"❌ Could not import Rust module: {e}")
        print("Make sure to build the Rust module first:")
        print("cd src/rust && cargo build --release")
        return None, 0
    except Exception as e:
        print(f"❌ Rust processing error: {e}")
        return None, 0

def test_cpp_processing(csv_path):
    """Test C++-based processing (if available)."""
    print("\n=== C++ Processing ===")
    
    try:
        # Check if C++ components are available
        cpp_dir = Path("src/cpp")
        if cpp_dir.exists():
            print("C++ source directory found")
            
            # For now, just check if we can compile
            import subprocess
            result = subprocess.run(['g++', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ C++ compiler available: {result.stdout.split()[2]}")
                print("C++ components ready for integration")
                return True, 0
            else:
                print("❌ C++ compiler not available")
                return False, 0
        else:
            print("C++ source directory not found")
            return False, 0
            
    except Exception as e:
        print(f"❌ C++ processing error: {e}")
        return False, 0

def compare_performance(python_time, rust_time, cpp_available):
    """Compare performance between Python and Rust."""
    print("\n=== Performance Comparison ===")
    
    if rust_time > 0:
        speedup = python_time / rust_time
        print(f"Python processing time: {python_time:.3f} seconds")
        print(f"Rust processing time: {rust_time:.3f} seconds")
        print(f"Rust speedup: {speedup:.1f}x faster")
        
        if speedup > 1:
            print("✅ Rust processing is faster!")
        else:
            print("⚠️ Python processing is faster (this might be due to overhead)")
    else:
        print("❌ Could not compare performance - Rust processing failed")
    
    if cpp_available:
        print("✅ C++ components available for future optimization")

def main():
    """Main test function."""
    print("🚀 Rust/C++ Data Processing Test")
    print("=" * 50)
    
    # Create test data
    csv_path, original_df = create_test_csv()
    
    # Test Python processing
    python_df, python_time = test_python_processing(csv_path)
    
    # Test Rust processing
    rust_result, rust_time = test_rust_processing(csv_path)
    
    # Test C++ availability
    cpp_available, _ = test_cpp_processing(csv_path)
    
    # Compare performance
    compare_performance(python_time, rust_time, cpp_available)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    print(f"✅ Test data created: {len(original_df)} rows")
    print(f"✅ Python processing: {python_time:.3f}s")
    
    if rust_result:
        print(f"✅ Rust processing: {rust_time:.3f}s")
    else:
        print("❌ Rust processing: Failed")
    
    if cpp_available:
        print("✅ C++ components: Available")
    else:
        print("⚠️ C++ components: Not available")
    
    print("\n🎉 Test completed!")
    print("\nNext steps:")
    print("1. Optimize Rust processing for better performance")
    print("2. Integrate C++ SIMD components")
    print("3. Test with larger datasets")
    print("4. Run full pipeline integration")

if __name__ == "__main__":
    main() 