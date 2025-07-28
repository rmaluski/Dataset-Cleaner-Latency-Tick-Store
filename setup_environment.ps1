# PowerShell script to set up the development environment
# Run this script to configure your environment for the Dataset Cleaner project

Write-Host "Setting up Dataset Cleaner development environment..." -ForegroundColor Green

# Add MinGW to PATH for this session
$env:PATH += ";C:\msys64\mingw64\bin"

# Verify components
Write-Host "`nVerifying components..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found" -ForegroundColor Red
}

# Check C++ compiler
try {
    $gppVersion = g++ --version 2>&1 | Select-Object -First 1
    Write-Host "✅ C++ Compiler: $gppVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ C++ compiler not found" -ForegroundColor Red
}

# Check Rust
try {
    $rustVersion = cargo --version 2>&1
    Write-Host "✅ Rust: $rustVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Rust not found" -ForegroundColor Red
}

# Test Python dependencies
Write-Host "`nTesting Python dependencies..." -ForegroundColor Yellow
try {
    python -c "import pyarrow, duckdb, pandas, numpy, great_expectations, pandera; print('✅ All Python dependencies available')"
} catch {
    Write-Host "❌ Some Python dependencies missing" -ForegroundColor Red
}

# Test Rust build
Write-Host "`nTesting Rust build..." -ForegroundColor Yellow
try {
    Set-Location "src\rust"
    cargo check
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Rust project compiles successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Rust compilation failed" -ForegroundColor Red
    }
    Set-Location "..\.."
} catch {
    Write-Host "❌ Rust build test failed" -ForegroundColor Red
}

Write-Host "`n🎉 Environment setup complete!" -ForegroundColor Green
Write-Host "`nTo make the C++ compiler available permanently, add this to your PATH:" -ForegroundColor Yellow
Write-Host "C:\msys64\mingw64\bin" -ForegroundColor Cyan
Write-Host "`nYou can do this by:" -ForegroundColor Yellow
Write-Host "1. Open System Properties > Advanced > Environment Variables" -ForegroundColor White
Write-Host "2. Edit the PATH variable" -ForegroundColor White
Write-Host "3. Add: C:\msys64\mingw64\bin" -ForegroundColor White

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Run: python test_integration.py" -ForegroundColor White
Write-Host "2. Run: python examples/basic_usage.py" -ForegroundColor White
Write-Host "3. Build Rust: cd src\rust && cargo build --release" -ForegroundColor White 