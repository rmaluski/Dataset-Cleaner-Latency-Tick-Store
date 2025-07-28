#!/usr/bin/env python3
"""
Integration test script to verify all components are working.
"""

import sys
import subprocess
import os

def test_python_dependencies():
    """Test Python dependencies."""
    print("Testing Python dependencies...")
    
    try:
        import pyarrow
        print(f"✅ PyArrow {pyarrow.__version__}")
        
        import duckdb
        print(f"✅ DuckDB {duckdb.__version__}")
        
        import pandas
        print(f"✅ Pandas {pandas.__version__}")
        
        import numpy
        print(f"✅ NumPy {numpy.__version__}")
        
        import great_expectations
        print(f"✅ Great Expectations {great_expectations.__version__}")
        
        import pandera
        print(f"✅ Pandera {pandera.__version__}")
        
        return True
    except ImportError as e:
        print(f"❌ Python dependency error: {e}")
        return False

def test_cpp_compiler():
    """Test C++ compiler."""
    print("\nTesting C++ compiler...")
    
    try:
        result = subprocess.run(['g++', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ C++ Compiler: {result.stdout.split()[2]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ C++ compiler error: {e}")
        return False

def test_rust_components():
    """Test Rust components."""
    print("\nTesting Rust components...")
    
    try:
        # Check if Rust is installed
        result = subprocess.run(['cargo', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Rust: {result.stdout.strip()}")
        
        # Check if we can build the Rust project
        rust_dir = os.path.join('src', 'rust')
        if os.path.exists(rust_dir):
            result = subprocess.run(['cargo', 'check'], 
                                  cwd=rust_dir, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Rust project compiles successfully")
                return True
            else:
                print(f"❌ Rust compilation error: {result.stderr}")
                return False
        else:
            print("❌ Rust source directory not found")
            return False
            
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Rust error: {e}")
        return False

def test_sample_data_processing():
    """Test sample data processing."""
    print("\nTesting sample data processing...")
    
    try:
        import pandas as pd
        import pyarrow as pa
        
        # Create sample data
        data = {
            'timestamp': ['2025-01-27T09:30:00', '2025-01-27T09:30:01'],
            'symbol': ['ES', 'ES'],
            'price': [4500.25, 4500.50],
            'size': [100, 200]
        }
        
        # Test Pandas
        df = pd.DataFrame(data)
        print(f"✅ Pandas DataFrame created: {len(df)} rows")
        
        # Test PyArrow
        table = pa.Table.from_pandas(df)
        print(f"✅ PyArrow Table created: {table.num_rows} rows")
        
        # Test DuckDB
        import duckdb
        con = duckdb.connect(':memory:')
        # Create table from DataFrame
        con.execute("CREATE TABLE ticks AS SELECT * FROM df")
        result = con.execute("SELECT COUNT(*) FROM ticks").fetchone()
        print(f"✅ DuckDB query executed: {result[0]} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Data processing error: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Dataset Cleaner + Latency Tick-Store Integration Test")
    print("=" * 60)
    
    tests = [
        ("Python Dependencies", test_python_dependencies),
        ("C++ Compiler", test_cpp_compiler),
        ("Rust Components", test_rust_components),
        ("Sample Data Processing", test_sample_data_processing),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your environment is ready for development.")
        print("\nNext steps:")
        print("1. Run: python examples/basic_usage.py")
        print("2. Start development with: python -m tickdb")
        print("3. Build with: cargo build --release (in src/rust)")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 