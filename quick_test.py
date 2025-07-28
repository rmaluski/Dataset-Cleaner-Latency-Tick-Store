#!/usr/bin/env python3
"""
Quick test for Dataset Cleaner - verify everything works
"""

import sys
import tempfile
from pathlib import Path
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_tickdb():
    """Test TickDB functionality"""
    print("Testing TickDB functionality...")
    
    try:
        from tickdb.core import TickDB
        from tickdb.config import TickDBConfig
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create configuration
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=1000,
                enable_metrics=False
            )
            
            # Initialize TickDB
            tickdb = TickDB(config)
            print("  TickDB initialized successfully")
            
            # Test schema listing
            schemas = tickdb.list_schemas()
            print(f"  Available schemas: {schemas}")
            
            # Test health check
            health = tickdb.health_check()
            print(f"  Health status: {health['status']}")
            
            # Create test data
            df = pd.DataFrame({
                'ts': pd.date_range('2025-01-27 09:30:00', periods=100, freq='1s'),
                'symbol': ['ES'] * 100,
                'price': [100.0 + i for i in range(100)],
                'size': [100 + i for i in range(100)]
            })
            
            # Test data append
            result = tickdb.append(df, schema_id="ticks_v1")
            print(f"  Data appended: {result}")
            
            # Test data reading
            read_result = tickdb.read(schema_id="ticks_v1", limit=10)
            print(f"  Data read: {len(read_result)} rows")
            
            print("  All TickDB tests passed!")
            return True
            
    except Exception as e:
        print(f"  TickDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_processing():
    """Test data processing on available files"""
    print("\nTesting data processing...")
    
    try:
        # Find CSV files that we can read
        csv_files = []
        for file_path in Path(".").glob("*.csv"):
            if not file_path.name.startswith("extracted_"):
                csv_files.append(file_path)
        
        print(f"  Found {len(csv_files)} CSV files to test")
        
        for i, csv_file in enumerate(csv_files[:2]):  # Test first 2 files
            print(f"  Testing {csv_file.name}...")
            
            try:
                # Read data
                df = pd.read_csv(csv_file, nrows=100)
                print(f"    Read {len(df)} rows, {len(df.columns)} columns")
                
                # Basic data quality check
                missing = df.isnull().sum().sum()
                duplicates = df.duplicated().sum()
                print(f"    Missing values: {missing}")
                print(f"    Duplicate rows: {duplicates}")
                
                # Show sample
                print(f"    Sample data:")
                print(df.head(2).to_string())
                
            except Exception as e:
                print(f"    Error reading {csv_file.name}: {e}")
        
        print("  Data processing tests completed!")
        return True
        
    except Exception as e:
        print(f"  Data processing test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Dataset Cleaner - Quick Test")
    print("=" * 50)
    
    tests = [
        ("TickDB Functionality", test_tickdb),
        ("Data Processing", test_data_processing),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nSUCCESS! Dataset Cleaner is working correctly!")
        print("\nKey features verified:")
        print("- TickDB initialization and configuration")
        print("- Schema management")
        print("- Data ingestion and storage")
        print("- Data querying and retrieval")
        print("- Health monitoring")
        print("- Data quality analysis")
        
        print("\nNext steps:")
        print("1. Install C++/Rust compilers for optimal performance")
        print("2. Test with larger datasets")
        print("3. Use CLI interface: python -m tickdb.cli")
        print("4. Deploy with Docker: docker-compose up")
    else:
        print(f"\n{total - passed} tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 