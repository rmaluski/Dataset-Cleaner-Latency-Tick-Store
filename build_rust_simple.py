#!/usr/bin/env python3
"""
Simple Rust Extension Builder
"""

import os
import sys
import subprocess
import shutil
import tempfile

def print_step(message):
    print(f"\n🔧 {message}")

def check_rust():
    """Check if Rust is available"""
    print_step("Checking Rust...")
    
    try:
        result = subprocess.run(['cargo', '--version'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            version_line = result.stdout.strip()
            print(f"✅ Found: {version_line}")
            return True
        else:
            print("❌ Cargo not found")
            return False
            
    except Exception as e:
        print(f"❌ Rust check failed: {e}")
        return False

def build_rust_extension():
    """Build the Rust extension"""
    print_step("Building Rust extension...")
    
    # Create a temporary directory without special characters
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"✅ Using temp directory: {temp_dir}")
        
        # Copy Rust source files to temp directory
        rust_src = "src/rust"
        temp_rust = os.path.join(temp_dir, "rust_project")
        
        if os.path.exists(rust_src):
            shutil.copytree(rust_src, temp_rust)
            print(f"✅ Copied Rust source to: {temp_rust}")
        else:
            print(f"❌ Rust source not found: {rust_src}")
            return False
        
        # Change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_rust)
        
        try:
            # Build Rust extension
            print("Building Rust extension...")
            result = subprocess.run(['cargo', 'build', '--release'], 
                                  capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ Rust build successful!")
                
                # Find the built library
                target_dir = os.path.join(temp_rust, "target", "release")
                if os.path.exists(target_dir):
                    # Look for the library file
                    for file in os.listdir(target_dir):
                        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib'):
                            lib_path = os.path.join(target_dir, file)
                            print(f"✅ Found library: {lib_path}")
                            
                            # Copy to project root with Python extension name
                            dest_name = "dataset_core_rust.cp311-win_amd64.pyd"
                            dest_path = os.path.join(original_dir, dest_name)
                            
                            shutil.copy2(lib_path, dest_path)
                            print(f"✅ Copied to: {dest_path}")
                            
                            return True
                
                print("❌ Library file not found")
                return False
            else:
                print("❌ Rust build failed!")
                print(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Rust build timed out")
            return False
        except Exception as e:
            print(f"❌ Rust build error: {e}")
            return False
        finally:
            os.chdir(original_dir)

def test_rust_extension():
    """Test the built Rust extension"""
    print_step("Testing Rust extension...")
    
    try:
        import dataset_core_rust
        print("✅ Rust extension imported successfully!")
        
        # Create test data
        test_csv = "test_rust_simple.csv"
        with open(test_csv, 'w') as f:
            f.write("timestamp,price,volume\n")
            f.write("2023-01-01,100.0,1000\n")
            f.write("2023-01-02,101.0,1100\n")
            f.write("2023-01-03,102.0,1200\n")
        
        # Test parsing
        result = dataset_core_rust.parse_csv_simd(test_csv, 1024)
        
        print(f"✅ Parsing test successful!")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Rows processed: {result.get('rows_processed', 0)}")
        print(f"   Processing time: {result.get('processing_time_ms', 0):.3f}ms")
        print(f"   Throughput: {result.get('throughput_mbps', 0):.1f} MB/s")
        
        # Cleanup
        os.remove(test_csv)
        
        return True
        
    except ImportError as e:
        print(f"❌ Rust extension import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Rust extension test failed: {e}")
        return False

def main():
    """Main build function"""
    print("="*60)
    print("  Simple Rust Extension Builder")
    print("="*60)
    
    # Check Rust
    if not check_rust():
        print("\n❌ Rust not available")
        return False
    
    # Build extension
    if not build_rust_extension():
        print("\n❌ Build failed")
        return False
    
    # Test extension
    if not test_rust_extension():
        print("\n❌ Extension test failed")
        return False
    
    print("\n🎉 Rust extension is ready for use!")
    print("   You can now import 'dataset_core_rust' in Python")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 