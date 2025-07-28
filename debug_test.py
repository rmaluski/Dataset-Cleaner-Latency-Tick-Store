#!/usr/bin/env python3
"""
Debug test to identify issues with TickDB initialization
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test basic imports."""
    print("Testing imports...")
    
    try:
        print("  Importing config...")
        from tickdb.config import TickDBConfig
        print("  ✅ TickDBConfig imported")
        
        print("  Importing schemas...")
        from tickdb.schemas import SchemaRegistry
        print("  ✅ SchemaRegistry imported")
        
        print("  Importing core...")
        from tickdb.core import TickDB
        print("  ✅ TickDB imported")
        
        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test configuration creation."""
    print("\nTesting configuration...")
    
    try:
        from tickdb.config import TickDBConfig
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=1000,
                enable_metrics=False
            )
            
            print(f"  ✅ Configuration created: {config}")
            return True
            
    except Exception as e:
        print(f"  ❌ Configuration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schema_registry():
    """Test schema registry."""
    print("\nTesting schema registry...")
    
    try:
        from tickdb.schemas import SchemaRegistry
        
        registry = SchemaRegistry()
        schemas = registry.list_schemas()
        
        print(f"  ✅ Schema registry created, found {len(schemas)} schemas")
        print(f"  📋 Schemas: {schemas}")
        return True
        
    except Exception as e:
        print(f"  ❌ Schema registry failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tickdb_init():
    """Test TickDB initialization."""
    print("\nTesting TickDB initialization...")
    
    try:
        from tickdb.core import TickDB
        from tickdb.config import TickDBConfig
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = TickDBConfig(
                data_path=temp_path / "data",
                quarantine_path=temp_path / "quarantine",
                batch_size=1000,
                enable_metrics=False
            )
            
            print("  Creating TickDB instance...")
            tickdb = TickDB(config)
            print("  ✅ TickDB created successfully")
            
            # Test basic methods
            print("  Testing list_schemas...")
            schemas = tickdb.list_schemas()
            print(f"  ✅ Found {len(schemas)} schemas")
            
            print("  Testing health_check...")
            health = tickdb.health_check()
            print(f"  ✅ Health check: {health}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ TickDB initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run debug tests."""
    print("🔍 Debug Test for Dataset Cleaner")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Schema Registry", test_schema_registry),
        ("TickDB Initialization", test_tickdb_init),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        if not result:
            print(f"\n❌ Test '{test_name}' failed. Stopping.")
            break
        print(f"✅ {test_name} passed")
    
    print("\n🎉 Debug test completed!")

if __name__ == "__main__":
    main() 