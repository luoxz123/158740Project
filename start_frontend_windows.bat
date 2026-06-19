@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=80"

py -3 --version >nul 2>nul
if not errorlevel 1 (
  start "NZ Renewable Frontend" cmd /k "py -3 -m http.server %FRONTEND_PORT% -d frontend"
  start "" "http://localhost:%FRONTEND_PORT%/"
  exit /b 0
)

python --version >nul 2>nul
if not errorlevel 1 (
  start "NZ Renewable Frontend" cmd /k "python -m http.server %FRONTEND_PORT% -d frontend"
  start "" "http://localhost:%FRONTEND_PORT%/"
  exit /b 0
)

echo ERROR: Python was not found.
pause
exit /b 1
