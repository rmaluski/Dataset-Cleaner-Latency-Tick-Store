#!/usr/bin/env python3
"""
Simple test script for Dataset Cleaner + Latency Tick-Store
Tests basic functionality without complex dependencies
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_functionality():
    """Test basic TickDB functionality."""
    print("🧪 Testing Dataset Cleaner + Latency Tick-Store")
    print("=" * 60)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from tickdb.core import TickDB, TickDBConfig
        from tickdb.schemas import SchemaRegistry
        print("   ✅ All imports successful")
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test configuration
            print("2. Testing configuration...")
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=1000,
                enable_metrics=False
            )
            print("   ✅ Configuration created")
            
            # Test TickDB initialization
            print("3. Testing TickDB initialization...")
            tickdb = TickDB(config)
            print("   ✅ TickDB initialized")
            
            # Test schema registry
            print("4. Testing schema registry...")
            schemas = tickdb.list_schemas()
            assert "ticks_v1" in schemas
            assert "alt_nvd_v1" in schemas
            print(f"   ✅ Found schemas: {schemas}")
            
            # Test schema retrieval
            print("5. Testing schema retrieval...")
            schema = tickdb.get_schema("ticks_v1")
            assert schema["id"] == "ticks_v1"
            print("   ✅ Schema retrieval successful")
            
            # Test data creation and ingestion
            print("6. Testing data ingestion...")
            df = create_test_data(100)
            result = tickdb.append(df, "ticks_v1", "test_source")
            assert result["rows_processed"] == 100
            assert result["rows_failed"] == 0
            print("   ✅ Data ingestion successful")
            
            # Test data querying
            print("7. Testing data querying...")
            result = tickdb.read(symbol="ES", fields=["ts", "price", "size"])
            assert len(result) > 0
            print(f"   ✅ Query returned {len(result)} rows")
            
            # Test time-range querying
            print("8. Testing time-range querying...")
            start_time = "2025-01-27T09:30:00Z"
            end_time = "2025-01-27T09:31:00Z"
            result = tickdb.read(
                symbol="ES",
                ts_start=start_time,
                ts_end=end_time,
                fields=["ts", "price"]
            )
            print(f"   ✅ Time-range query returned {len(result)} rows")
            
            # Test health check
            print("9. Testing health check...")
            health = tickdb.health_check()
            assert health["status"] == "healthy"
            print("   ✅ Health check passed")
            
            print("\n🎉 ALL TESTS PASSED!")
            return True
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_data(n_rows=100):
    """Create test tick data."""
    timestamps = pd.date_range(
        '2025-01-27 09:30:00', 
        periods=n_rows, 
        freq='1s'
    )
    
    data = {
        'ts': timestamps,
        'symbol': np.random.choice(['ES', 'NQ', 'YM'], n_rows),
        'price': np.random.uniform(4000, 5000, n_rows),
        'size': np.random.randint(1, 1000, n_rows),
        'bid': np.random.uniform(4000, 5000, n_rows),
        'ask': np.random.uniform(4000, 5000, n_rows),
    }
    
    return pd.DataFrame(data)

def test_performance():
    """Test performance characteristics."""
    print("\n🚀 Testing Performance Characteristics")
    print("=" * 60)
    
    try:
        from tickdb.core import TickDB, TickDBConfig
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=16384,
                enable_metrics=False
            )
            
            tickdb = TickDB(config)
            
            # Test ingestion performance
            print("1. Testing ingestion performance...")
            df = create_test_data(10000)  # 10K rows
            
            start_time = time.time()
            result = tickdb.append(df, "ticks_v1", "perf_test")
            end_time = time.time()
            
            ingestion_time = end_time - start_time
            data_size_mb = len(df) * df.memory_usage(deep=True).sum() / (1024 * 1024)
            throughput_mbps = data_size_mb / ingestion_time
            
            print(f"   📊 Ingested {len(df):,} rows in {ingestion_time:.3f}s")
            print(f"   📊 Throughput: {throughput_mbps:.2f} MB/s")
            
            # Test query performance
            print("2. Testing query performance...")
            start_time = time.time()
            result = tickdb.read(symbol="ES", fields=["ts", "price", "size"])
            end_time = time.time()
            
            query_time = (end_time - start_time) * 1000  # Convert to ms
            print(f"   📊 Query returned {len(result):,} rows in {query_time:.2f}ms")
            
            # Test filtered query performance
            print("3. Testing filtered query performance...")
            start_time = time.time()
            result = tickdb.read(
                symbol="ES",
                ts_start="2025-01-27T09:30:00Z",
                ts_end="2025-01-27T09:30:30Z",
                fields=["ts", "price"]
            )
            end_time = time.time()
            
            filter_time = (end_time - start_time) * 1000  # Convert to ms
            print(f"   📊 Filtered query returned {len(result):,} rows in {filter_time:.2f}ms")
            
            print("\n🎉 Performance tests completed!")
            return True
            
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and validation."""
    print("\n🛡️ Testing Error Handling")
    print("=" * 60)
    
    try:
        from tickdb.core import TickDB, TickDBConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                enable_metrics=False
            )
            
            tickdb = TickDB(config)
            
            # Test invalid schema
            print("1. Testing invalid schema handling...")
            try:
                tickdb.get_schema("invalid_schema")
                print("   ❌ Should have raised KeyError")
                return False
            except KeyError:
                print("   ✅ Correctly handled invalid schema")
            
            # Test data with missing required fields
            print("2. Testing missing required fields...")
            df_invalid = pd.DataFrame({
                'ts': pd.date_range('2025-01-27 09:30:00', periods=10, freq='1s'),
                'price': [100.0] * 10,
                'size': [100] * 10
                # Missing 'symbol' field
            })
            
            result = tickdb.append(df_invalid, "ticks_v1", "error_test")
            print(f"   📊 Invalid data: {result['rows_processed']} processed, {result['rows_failed']} failed")
            
            # Test data with invalid values
            print("3. Testing invalid values...")
            df_negative = pd.DataFrame({
                'ts': pd.date_range('2025-01-27 09:30:00', periods=10, freq='1s'),
                'symbol': ['ES'] * 10,
                'price': [-100.0] * 10,  # Negative prices
                'size': [100] * 10
            })
            
            result = tickdb.append(df_negative, "ticks_v1", "error_test")
            print(f"   📊 Negative prices: {result['rows_processed']} processed, {result['rows_failed']} failed")
            
            print("\n🎉 Error handling tests completed!")
            return True
            
    except Exception as e:
        print(f"\n❌ Error handling test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Dataset Cleaner + Latency Tick-Store - Comprehensive Testing")
    print("=" * 80)
    
    # Install required packages if not available
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        print("Installing required packages...")
        os.system("pip install pandas numpy pyarrow")
    
    # Run tests
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Performance", test_performance),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "="*80)
    print("📋 TEST SUMMARY")
    print("="*80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your Dataset Cleaner is working correctly!")
        print("\nNext steps:")
        print("1. Run performance benchmark: python benchmark.py")
        print("2. Start the service: python -m tickdb.cli")
        print("3. View documentation: cat README.md")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 