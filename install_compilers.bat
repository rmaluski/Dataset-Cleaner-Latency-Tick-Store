@echo off
echo Installing C++ and Rust Compilers for Dataset Cleaner
echo ====================================================

echo.
echo Step 1: Installing Rust...
echo Downloading Rust installer...
powershell -Command "Invoke-WebRequest -Uri https://win.rustup.rs -OutFile rustup-init.exe"
echo Running Rust installer...
rustup-init.exe --quiet --default-toolchain stable --profile default
del rustup-init.exe

echo.
echo Step 2: Installing Visual Studio Build Tools...
echo Downloading VS Build Tools...
powershell -Command "Invoke-WebRequest -Uri https://aka.ms/vs/17/release/vs_buildtools.exe -OutFile vs_buildtools.exe"
echo Running VS Build Tools installer...
vs_buildtools.exe --quiet --wait --norestart --nocache --installPath "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools" --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.Windows10SDK.19041
del vs_buildtools.exe

echo.
echo Step 3: Setting up environment...
echo Refreshing PATH...
call refreshenv.cmd 2>nul || (
    echo Please restart your terminal or run: refreshenv
)

echo.
echo Installation complete!
echo.
echo To verify installation, run:
echo   rustc --version
echo   cl
echo.
echo Then run: python build_windows_simple.py
pause 