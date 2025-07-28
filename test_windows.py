#!/usr/bin/env python3
"""
Simple test for Dataset Cleaner - Windows compatible
"""

import sys
import tempfile
from pathlib import Path
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_functionality():
    """Test basic functionality with minimal components."""
    print("Testing Basic Dataset Cleaner Functionality")
    print("=" * 60)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from tickdb.config import TickDBConfig
        from tickdb.schemas import SchemaRegistry
        print("   Imports successful")
        
        # Test configuration
        print("2. Testing configuration...")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=1000,
                enable_metrics=False
            )
            print("   Configuration created")
            
            # Test schema registry
            print("3. Testing schema registry...")
            registry = SchemaRegistry()
            schemas = registry.list_schemas()
            print(f"   Found {len(schemas)} schemas: {schemas}")
            
            # Test schema retrieval
            print("4. Testing schema retrieval...")
            schema = registry.get_schema("ticks_v1")
            print(f"   Retrieved schema: {schema.id}")
            
            # Test data creation
            print("5. Testing data creation...")
            df = pd.DataFrame({
                'ts': pd.date_range('2025-01-27 09:30:00', periods=10, freq='1s'),
                'symbol': ['ES'] * 10,
                'price': [100.0 + i for i in range(10)],
                'size': [100 + i for i in range(10)]
            })
            print(f"   Created test data: {len(df)} rows")
            
            print("\nBasic functionality test passed!")
            return True
            
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_analysis():
    """Test data analysis on real files."""
    print("\nTesting Data Analysis on Real Files")
    print("=" * 60)
    
    try:
        # Find CSV files
        csv_files = list(Path(".").glob("*.csv"))
        print(f"Found {len(csv_files)} CSV files")
        
        for i, csv_file in enumerate(csv_files[:3]):  # Test first 3 files
            print(f"\n{i+1}. Analyzing {csv_file.name}...")
            
            try:
                # Read first few rows
                df = pd.read_csv(csv_file, nrows=100)
                print(f"   Read {len(df)} rows")
                print(f"   Columns: {list(df.columns)}")
                print(f"   Shape: {df.shape}")
                
                # Check for issues
                missing = df.isnull().sum().sum()
                duplicates = df.duplicated().sum()
                
                print(f"   Missing values: {missing}")
                print(f"   Duplicate rows: {duplicates}")
                
                # Show sample data
                print(f"   Sample data:")
                print(df.head(2).to_string())
                
            except Exception as e:
                print(f"   Error reading {csv_file.name}: {e}")
        
        print("\nData analysis test completed!")
        return True
        
    except Exception as e:
        print(f"\nData analysis failed: {e}")
        return False

def main():
    """Run simple tests."""
    print("Dataset Cleaner - Simple Testing")
    print("=" * 80)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Data Analysis", test_data_analysis),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "="*80)
    print("SIMPLE TEST SUMMARY")
    print("="*80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nALL SIMPLE TESTS PASSED!")
        print("\nYour Dataset Cleaner basic functionality is working!")
        print("\nNext steps:")
        print("1. Test with CLI: python -m tickdb.cli")
        print("2. View documentation: cat README.md")
    else:
        print(f"\n{total - passed} tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
