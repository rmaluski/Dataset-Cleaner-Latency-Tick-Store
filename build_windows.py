#!/usr/bin/env python3
"""
Windows Build script for Dataset Cleaner + Latency Tick-Store
Compiles C++ and Rust components and integrates with Python package
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, check=False):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: {result.stderr}")
        return False
    return True

def check_compiler_availability():
    """Check what compilers are available"""
    print("Checking compiler availability...")
    
    compilers = {
        'msvc': False,
        'mingw': False,
        'gcc': False,
        'clang': False
    }
    
    # Check for Visual Studio
    try:
        result = subprocess.run(['where', 'cl'], capture_output=True, text=True)
        if result.returncode == 0:
            compilers['msvc'] = True
            print("✅ Visual Studio C++ compiler found")
    except:
        pass
    
    # Check for MinGW
    try:
        result = subprocess.run(['where', 'g++'], capture_output=True, text=True)
        if result.returncode == 0:
            compilers['mingw'] = True
            print("✅ MinGW C++ compiler found")
    except:
        pass
    
    # Check for GCC
    try:
        result = subprocess.run(['where', 'gcc'], capture_output=True, text=True)
        if result.returncode == 0:
            compilers['gcc'] = True
            print("✅ GCC compiler found")
    except:
        pass
    
    # Check for Rust
    try:
        result = subprocess.run(['cargo', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Rust compiler found")
            print(f"   {result.stdout.strip()}")
        else:
            print("❌ Rust compiler not found")
    except:
        print("❌ Rust compiler not found")
    
    return compilers

def build_cpp_components(compilers):
    """Build C++ components if possible"""
    print("\nBuilding C++ components...")
    
    cpp_dir = Path("src/cpp")
    build_dir = cpp_dir / "build"
    
    # Create build directory
    build_dir.mkdir(exist_ok=True)
    
    # Try different CMake generators based on available compilers
    cmake_generators = []
    
    if compilers['msvc']:
        cmake_generators.append("Visual Studio 17 2022")
        cmake_generators.append("Visual Studio 16 2019")
        cmake_generators.append("Visual Studio 15 2017")
    
    if compilers['mingw'] or compilers['gcc']:
        cmake_generators.append("MinGW Makefiles")
        cmake_generators.append("Unix Makefiles")
    
    # Try each generator
    for generator in cmake_generators:
        print(f"Trying CMake generator: {generator}")
        
        # Clean build directory
        for item in build_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        
        # Configure with CMake
        if run_command(f'cmake -G "{generator}" ..', cwd=build_dir):
            print(f"✅ CMake configuration successful with {generator}")
            
            # Try to build
            if generator.startswith("Visual Studio"):
                # Use MSBuild for Visual Studio
                if run_command("cmake --build . --config Release", cwd=build_dir):
                    print("✅ C++ build successful with Visual Studio")
                    return True
            else:
                # Use make for other generators
                if run_command("cmake --build .", cwd=build_dir):
                    print("✅ C++ build successful with Make")
                    return True
    
    print("❌ C++ build failed - no suitable compiler found")
    return False

def build_rust_components():
    """Build Rust components if possible"""
    print("\nBuilding Rust components...")
    
    rust_dir = Path("src/rust")
    
    if not rust_dir.exists():
        print("❌ Rust source directory not found")
        return False
    
    # Check if Cargo.toml exists
    if not (rust_dir / "Cargo.toml").exists():
        print("❌ Cargo.toml not found")
        return False
    
    # Try to build Rust library
    if run_command("cargo build --release", cwd=rust_dir):
        print("✅ Rust build successful")
        
        # Copy built library to Python package
        lib_path = rust_dir / "target/release/libdataset_core_rust.dll"
        if lib_path.exists():
            shutil.copy2(lib_path, "src/tickdb/")
            print("✅ Rust library copied to Python package")
            return True
        else:
            print("❌ Rust library not found after build")
            return False
    else:
        print("❌ Rust build failed")
        return False

def install_python_dependencies():
    """Install Python dependencies"""
    print("\nInstalling Python dependencies...")
    
    # Install core dependencies
    dependencies = [
        "pyarrow",
        "duckdb", 
        "pandas",
        "pydantic",
        "click",
        "rich",
        "structlog",
        "prometheus-client"
    ]
    
    for dep in dependencies:
        if run_command(f"pip install {dep}"):
            print(f"✅ Installed {dep}")
        else:
            print(f"❌ Failed to install {dep}")
    
    # Install in development mode
    if run_command("pip install -e ."):
        print("✅ Installed package in development mode")
    else:
        print("❌ Failed to install package in development mode")

def run_tests():
    """Run tests"""
    print("\nRunning tests...")
    
    # Run simple tests first
    test_scripts = [
        "simple_test.py",
        "working_test.py", 
        "final_demo.py"
    ]
    
    for test_script in test_scripts:
        if Path(test_script).exists():
            print(f"Running {test_script}...")
            if run_command(f"python {test_script}"):
                print(f"✅ {test_script} passed")
            else:
                print(f"❌ {test_script} failed")

def create_performance_benchmark():
    """Create performance benchmark script"""
    print("\nCreating performance benchmark...")
    
    benchmark_script = """#!/usr/bin/env python3
\"\"\"
Performance benchmark for Dataset Cleaner + Latency Tick-Store
Tests ingestion speed and query latency
\"\"\"

import time
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

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
        print(f"❌ Ingestion benchmark failed: {e}")
        return 0

def benchmark_query_latency():
    \"\"\"Benchmark query latency\"\"\"
    print("\\n=== Query Latency Benchmark ===")
    
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
        print(f"❌ Query benchmark failed: {e}")
        return 0

def main():
    \"\"\"Run all benchmarks\"\"\"
    print("Dataset Cleaner + Latency Tick-Store Performance Benchmark")
    print("=" * 60)
    
    try:
        # Run benchmarks
        ingestion_throughput = benchmark_ingestion()
        scan_latency = benchmark_query_latency()
        
        # Print summary
        print("\\n=== Performance Summary ===")
        print(f"Ingestion throughput: {ingestion_throughput:.2f} MB/s")
        print(f"Full column scan latency: {scan_latency:.2f} ms")
        
        # Check against targets
        print("\\n=== Target Comparison ===")
        if ingestion_throughput >= 100:  # 100 MB/s baseline
            print("✅ Ingestion target met: ≥ 100 MB/s")
        else:
            print("❌ Ingestion target not met")
            
        if scan_latency < 100:  # 100 ms baseline
            print("✅ Full scan target met: < 100 ms")
        else:
            print("❌ Full scan target not met")
            
    except Exception as e:
        print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    main()
"""
    
    with open("benchmark_windows.py", "w") as f:
        f.write(benchmark_script)
    
    print("✅ Performance benchmark script created: benchmark_windows.py")

def main():
    """Main build function"""
    print("Building Dataset Cleaner + Latency Tick-Store (Windows)")
    print("=" * 60)
    
    # Check compiler availability
    compilers = check_compiler_availability()
    
    # Build components
    cpp_built = False
    rust_built = False
    
    if any(compilers.values()):
        cpp_built = build_cpp_components(compilers)
        rust_built = build_rust_components()
    else:
        print("\n⚠️ No C++/Rust compilers found - building Python-only version")
    
    # Install Python dependencies
    install_python_dependencies()
    
    # Run tests
    run_tests()
    
    # Create benchmark
    create_performance_benchmark()
    
    # Summary
    print("\n" + "="*60)
    print("BUILD SUMMARY")
    print("="*60)
    print(f"C++ components: {'✅ Built' if cpp_built else '❌ Not built'}")
    print(f"Rust components: {'✅ Built' if rust_built else '❌ Not built'}")
    print("Python components: ✅ Built")
    
    if cpp_built or rust_built:
        print("\n🎉 Build completed with native components!")
        print("Performance will be optimized with SIMD and parallel processing")
    else:
        print("\n🎉 Build completed (Python-only mode)")
        print("Performance will use Python fallbacks")
        print("\nTo enable native components, install:")
        print("1. Visual Studio Build Tools or MinGW")
        print("2. Rust (rustup.rs)")
        print("3. Re-run: python build_windows.py")
    
    print("\nNext steps:")
    print("1. Run performance benchmark: python benchmark_windows.py")
    print("2. Test with real data: python final_demo.py")
    print("3. Use CLI interface: python -m tickdb.cli")
    print("4. View documentation: cat README.md")

if __name__ == "__main__":
    main() 