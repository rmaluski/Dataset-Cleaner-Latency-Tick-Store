#!/usr/bin/env python3
"""
Build script for Dataset Cleaner + Latency Tick-Store
Compiles C++ and Rust components and integrates with Python package
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def build_cpp_components():
    """Build C++ components"""
    print("Building C++ components...")
    
    cpp_dir = Path("src/cpp")
    build_dir = cpp_dir / "build"
    
    # Create build directory
    build_dir.mkdir(exist_ok=True)
    
    # Configure with CMake
    run_command("cmake ..", cwd=build_dir)
    
    # Build
    run_command("make -j$(nproc)", cwd=build_dir)
    
    # Copy built library to Python package
    lib_path = build_dir / "libdataset_core.so"
    if lib_path.exists():
        shutil.copy2(lib_path, "src/tickdb/")
        print("C++ library built successfully")

def build_rust_components():
    """Build Rust components"""
    print("Building Rust components...")
    
    rust_dir = Path("src/rust")
    
    # Build Rust library
    run_command("cargo build --release", cwd=rust_dir)
    
    # Copy built library to Python package
    lib_path = rust_dir / "target/release/libdataset_core_rust.so"
    if lib_path.exists():
        shutil.copy2(lib_path, "src/tickdb/")
        print("Rust library built successfully")

def install_python_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    run_command("pip install -e .")

def run_tests():
    """Run tests"""
    print("Running tests...")
    run_command("python -m pytest tests/ -v")

def create_performance_benchmark():
    """Create performance benchmark script"""
    print("Creating performance benchmark...")
    
    benchmark_script = """
#!/usr/bin/env python3
\"\"\"
Performance benchmark for Dataset Cleaner + Latency Tick-Store
Tests ingestion speed and query latency
\"\"\"

import time
import pandas as pd
import numpy as np
from pathlib import Path
import tickdb as db

def generate_test_data(size_mb=100):
    \"\"\"Generate test data for benchmarking\"\"\"
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
    \"\"\"Benchmark data ingestion speed\"\"\"
    print("\\n=== Ingestion Benchmark ===")
    
    # Initialize TickDB
    tickdb = db.TickDB()
    
    # Generate test data
    df = generate_test_data(100)  # 100MB
    
    # Measure ingestion time
    start_time = time.time()
    tickdb.append(df, schema_id="ticks_v1")
    end_time = time.time()
    
    ingestion_time = end_time - start_time
    data_size_mb = len(df) * df.memory_usage(deep=True).sum() / (1024 * 1024)
    throughput_mbps = data_size_mb / ingestion_time
    
    print(f"Data size: {data_size_mb:.2f} MB")
    print(f"Ingestion time: {ingestion_time:.2f} seconds")
    print(f"Throughput: {throughput_mbps:.2f} MB/s")
    
    return throughput_mbps

def benchmark_query_latency():
    \"\"\"Benchmark query latency\"\"\"
    print("\\n=== Query Latency Benchmark ===")
    
    tickdb = db.TickDB()
    
    # Generate larger dataset for query testing
    df = generate_test_data(1000)  # 1GB
    tickdb.append(df, schema_id="ticks_v1")
    
    # Test full column scan
    start_time = time.time()
    result = tickdb.read(symbol="ES", fields=["ts", "price", "size"])
    end_time = time.time()
    
    scan_time = (end_time - start_time) * 1000  # Convert to ms
    rows_scanned = len(result)
    
    print(f"Full column scan: {scan_time:.2f} ms for {rows_scanned:,} rows")
    
    # Test predicate-filtered scan
    start_time = time.time()
    result = tickdb.read(
        symbol="ES",
        ts_start="2025-01-27T09:30:00Z",
        ts_end="2025-01-27T09:31:00Z",
        fields=["ts", "price", "size"]
    )
    end_time = time.time()
    
    filter_time = (end_time - start_time) * 1000  # Convert to ms
    rows_filtered = len(result)
    
    print(f"Predicate-filtered scan: {filter_time:.2f} ms for {rows_filtered:,} rows")
    
    return scan_time, filter_time

def main():
    \"\"\"Run all benchmarks\"\"\"
    print("Dataset Cleaner + Latency Tick-Store Performance Benchmark")
    print("=" * 60)
    
    try:
        # Run benchmarks
        ingestion_throughput = benchmark_ingestion()
        scan_latency, filter_latency = benchmark_query_latency()
        
        # Print summary
        print("\\n=== Performance Summary ===")
        print(f"Ingestion throughput: {ingestion_throughput:.2f} MB/s")
        print(f"Full column scan latency: {scan_latency:.2f} ms")
        print(f"Predicate-filtered scan latency: {filter_latency:.2f} ms")
        
        # Check against targets
        print("\\n=== Target Comparison ===")
        if ingestion_throughput >= 600:  # 600 MB/s = 36 GB/min
            print("✅ Ingestion target met: ≥ 600 MB/s")
        else:
            print("❌ Ingestion target not met")
            
        if scan_latency < 20:
            print("✅ Full scan target met: < 20 ms")
        else:
            print("❌ Full scan target not met")
            
        if filter_latency < 5:
            print("✅ Filtered scan target met: < 5 ms")
        else:
            print("❌ Filtered scan target not met")
            
    except Exception as e:
        print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    main()
"""
    
    with open("benchmark.py", "w") as f:
        f.write(benchmark_script)
    
    # Make executable
    os.chmod("benchmark.py", 0o755)
    print("Performance benchmark script created")

def main():
    """Main build function"""
    print("Building Dataset Cleaner + Latency Tick-Store")
    print("=" * 50)
    
    # Check if we're on a supported platform
    if sys.platform not in ["linux", "linux2"]:
        print("Warning: C++/Rust components may not build on this platform")
        print("Only Python components will be built")
    
    try:
        # Build components
        if sys.platform in ["linux", "linux2"]:
            build_cpp_components()
            build_rust_components()
        
        # Install Python package
        install_python_dependencies()
        
        # Run tests
        run_tests()
        
        # Create benchmark
        create_performance_benchmark()
        
        print("\n✅ Build completed successfully!")
        print("\nNext steps:")
        print("1. Run performance benchmark: python benchmark.py")
        print("2. Start the service: python -m tickdb.cli")
        print("3. View documentation: cat README.md")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 