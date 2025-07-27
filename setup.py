#!/usr/bin/env python3
"""
Setup script for TickDB development environment.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def create_directories():
    """Create necessary directories."""
    directories = [
        "data",
        "quarantine", 
        "schemas",
        "monitoring/grafana/dashboards",
        "monitoring/grafana/datasources",
        "examples",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")


def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing Python dependencies...")
    
    # Install in development mode
    result = run_command("pip install -e .[dev]", "Installing TickDB in development mode")
    if not result:
        sys.exit(1)
    
    # Install additional development tools
    run_command("pip install pre-commit", "Installing pre-commit hooks")
    run_command("pre-commit install", "Setting up pre-commit hooks")


def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")
    result = run_command("pytest tests/ -v", "Running test suite")
    if not result:
        print("⚠️  Some tests failed, but continuing with setup")
    else:
        print("✅ All tests passed!")


def create_sample_data():
    """Create sample data for testing."""
    print("📊 Creating sample data...")
    
    # Check if sample CSV exists
    sample_csv = Path("examples/sample_ticks.csv")
    if not sample_csv.exists():
        print("⚠️  Sample CSV file not found, creating basic example...")
        
        # Create a simple sample CSV
        sample_data = """ts,symbol,price,size,side,exchange
2025-01-27T09:30:00.000000000,ES,4500.25,100,buy,CME
2025-01-27T09:30:00.100000000,ES,4500.50,200,sell,CME
2025-01-27T09:30:00.200000000,ES,4500.75,150,buy,CME
2025-01-27T09:30:00.300000000,ES,4501.00,300,sell,CME
2025-01-27T09:30:00.400000000,ES,4500.75,100,buy,CME"""
        
        sample_csv.write_text(sample_data)
        print("✅ Created sample CSV file")


def setup_monitoring():
    """Set up monitoring configuration."""
    print("📊 Setting up monitoring...")
    
    # Create Grafana datasource configuration
    datasource_config = {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "Prometheus",
                "type": "prometheus",
                "url": "http://prometheus:9090",
                "access": "proxy",
                "isDefault": True
            }
        ]
    }
    
    import json
    datasource_file = Path("monitoring/grafana/datasources/prometheus.yml")
    datasource_file.parent.mkdir(parents=True, exist_ok=True)
    datasource_file.write_text(json.dumps(datasource_config, indent=2))
    print("✅ Created Grafana datasource configuration")


def main():
    """Main setup function."""
    print("🚀 TickDB Development Environment Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    install_dependencies()
    
    # Run tests
    run_tests()
    
    # Create sample data
    create_sample_data()
    
    # Setup monitoring
    setup_monitoring()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Run the basic example: python examples/basic_usage.py")
    print("   2. Try the CLI: tickdb --help")
    print("   3. Start with Docker: docker-compose up -d")
    print("   4. Access Grafana: http://localhost:3000 (admin/admin)")
    print("   5. Access Prometheus: http://localhost:9090")
    
    print("\n💡 Useful commands:")
    print("   - tickdb load <source_id> <file_path> <schema_id>")
    print("   - tickdb query --symbol ES --limit 10")
    print("   - tickdb health")
    print("   - tickdb metrics")


if __name__ == "__main__":
    main() 