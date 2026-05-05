@echo off
setlocal EnableDelayedExpansion

if /I not "%CONDA_DEFAULT_ENV%"=="base" (
  echo [ERROR] Please activate conda env first: base
  echo [ERROR] Command: conda activate base
  exit /b 1
)

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

set "BUILD_DIR="
for /d %%D in ("%ROOT_DIR%\*_build") do set "BUILD_DIR=%%~fD"
if "%BUILD_DIR%"=="" (
  echo [ERROR] *_build directory not found.
  exit /b 1
)

set "DIST_DIR="
for /d %%D in ("%ROOT_DIR%\*_dist") do set "DIST_DIR=%%~fD"
if "%DIST_DIR%"=="" (
  echo [ERROR] *_dist directory not found.
  exit /b 1
)

set "COLLECTOR_PY="
for /r "%ROOT_DIR%" %%F in (collector.py) do (
  if "%COLLECTOR_PY%"=="" (
    echo %%~fF | findstr /i /c:"_tools\\" >nul
    if not errorlevel 1 set "COLLECTOR_PY=%%~fF"
  )
)
if "%COLLECTOR_PY%"=="" (
  echo [ERROR] collector.py not found.
  exit /b 1
)

set "PKG_WORK=%BUILD_DIR%\collector_pyinstaller"

echo [INFO] Building collector.exe in env: %CONDA_DEFAULT_ENV%
echo [INFO] Script: %COLLECTOR_PY%
python -m PyInstaller --noconfirm --clean --onefile --name collector "%COLLECTOR_PY%" --distpath "%DIST_DIR%" --workpath "%PKG_WORK%" --specpath "%PKG_WORK%"
if errorlevel 1 (
  echo [ERROR] Build failed.
  exit /b 1
)

echo [OK] Build done: %DIST_DIR%\collector.exe
exit /b 0

