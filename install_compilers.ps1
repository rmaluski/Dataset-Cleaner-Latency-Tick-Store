# PowerShell script to install C++ and Rust compilers
Write-Host "Installing C++ and Rust Compilers for Dataset Cleaner" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green

# Step 1: Install Rust
Write-Host "`nStep 1: Installing Rust..." -ForegroundColor Yellow
Write-Host "Downloading Rust installer..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://win.rustup.rs" -OutFile "rustup-init.exe"
Write-Host "Running Rust installer..." -ForegroundColor Cyan
Start-Process -FilePath "rustup-init.exe" -ArgumentList "--quiet", "--default-toolchain", "stable", "--profile", "default" -Wait
Remove-Item "rustup-init.exe" -ErrorAction SilentlyContinue

# Step 2: Install Visual Studio Build Tools
Write-Host "`nStep 2: Installing Visual Studio Build Tools..." -ForegroundColor Yellow
Write-Host "Downloading VS Build Tools..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vs_buildtools.exe" -OutFile "vs_buildtools.exe"
Write-Host "Running VS Build Tools installer..." -ForegroundColor Cyan
Start-Process -FilePath "vs_buildtools.exe" -ArgumentList "--quiet", "--wait", "--norestart", "--nocache", "--installPath", "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools", "--add", "Microsoft.VisualStudio.Workload.VCTools", "--add", "Microsoft.VisualStudio.Component.Windows10SDK.19041" -Wait
Remove-Item "vs_buildtools.exe" -ErrorAction SilentlyContinue

# Step 3: Refresh environment
Write-Host "`nStep 3: Setting up environment..." -ForegroundColor Yellow
Write-Host "Please restart your terminal or run: refreshenv" -ForegroundColor Cyan

Write-Host "`nInstallation complete!" -ForegroundColor Green
Write-Host "`nTo verify installation, run:" -ForegroundColor Cyan
Write-Host "  rustc --version" -ForegroundColor White
Write-Host "  cl" -ForegroundColor White
Write-Host "`nThen run: python build_windows_simple.py" -ForegroundColor Cyan

Read-Host "Press Enter to continue" 