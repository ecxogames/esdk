@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "EDK_ROOT=%%~fI"
set "EDK_TOOL=%~n0"
set "EDK_PYTHON_VERSION=3.11"
if exist "%EDK_ROOT%\requirements.txt" for /f "tokens=2 delims==" %%V in ('findstr /R /I /C:"^[ ]*python[ ]*==" "%EDK_ROOT%\requirements.txt"') do set "EDK_PYTHON_VERSION=%%V"
for /f "tokens=1,2 delims=." %%A in ("%EDK_PYTHON_VERSION%") do set "EDK_PYTHON_MINOR=%%A.%%B"
set "EDK_PYTHON="
for /f "usebackq delims=" %%P in (`py -%EDK_PYTHON_MINOR% -c "import sys; print(sys.executable)" 2^>nul`) do set "EDK_PYTHON=%%P"
if not defined EDK_PYTHON (
    where winget.exe >nul 2>nul || (echo   !! Windows Package Manager is required to install Python automatically.& exit /b 1)
    echo   ^> Installing Python %EDK_PYTHON_VERSION%...
    winget install --id Python.Python.%EDK_PYTHON_MINOR% --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity || exit /b 1
    for /f "usebackq delims=" %%P in (`py -%EDK_PYTHON_MINOR% -c "import sys; print(sys.executable)" 2^>nul`) do set "EDK_PYTHON=%%P"
)
if not defined EDK_PYTHON (echo   !! Python %EDK_PYTHON_VERSION% could not be located.& exit /b 1)
echo.
echo   EDK  %EDK_TOOL%
echo   OK Python %EDK_PYTHON_VERSION% is ready.
if /I "%~1"=="--check" (echo   OK Batch launcher is ready for %EDK_ROOT%.& exit /b 0)
pushd "%EDK_ROOT%" || exit /b 1
"%EDK_PYTHON%" "%EDK_ROOT%\engine\tooling\launcher.py" "%EDK_TOOL%" %*
set "EDK_EXIT=%ERRORLEVEL%"
popd
if not "%EDK_EXIT%"=="0" echo   !! %EDK_TOOL% stopped with exit code %EDK_EXIT%.
exit /b %EDK_EXIT%
