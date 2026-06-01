@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

rem -------------------------------
rem Windows VM deployment settings
rem -------------------------------
if "%DB_HOST%"=="" set "DB_HOST=localhost"
if "%DB_PORT%"=="" set "DB_PORT=5432"
if "%DB_NAME%"=="" set "DB_NAME=renewable_nz"
if "%DB_USER%"=="" set "DB_USER=postgres"
if "%POSTGRES_PASSWORD%"=="" set "POSTGRES_PASSWORD=Postgres123"
if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=8000"
if "%GEOSERVER_URL%"=="" set "GEOSERVER_URL=http://localhost:8080/geoserver"
if "%GEOSERVER_USER%"=="" set "GEOSERVER_USER=admin"
if "%GEOSERVER_PASSWORD%"=="" set "GEOSERVER_PASSWORD=geoserver"

set "PGPASSWORD=%POSTGRES_PASSWORD%"
set "DB_DSN=host=%DB_HOST% port=%DB_PORT% dbname=%DB_NAME% user=%DB_USER% password=%POSTGRES_PASSWORD%"

echo.
echo ============================================================
echo NZ Renewable Energy Suitability Explorer - Windows VM deploy
echo ============================================================
echo Project root: %CD%
echo Database: %DB_USER%@%DB_HOST%:%DB_PORT%/%DB_NAME%
echo Frontend: http://localhost:%FRONTEND_PORT%
echo.

call :find_python
if errorlevel 1 goto :fail

call :find_psql
if errorlevel 1 goto :fail

echo [1/9] Installing Python dependencies...
"%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [2/9] Checking PostgreSQL/PostGIS connection...
"%PSQL_EXE%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%DB_USER%" -d "%DB_NAME%" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"
if errorlevel 1 goto :fail

echo.
echo [3/9] Rebuilding renewable_nz schema and sample layers...
"%PSQL_EXE%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%DB_USER%" -d "%DB_NAME%" -v ON_ERROR_STOP=1 -f "database\schema.sql"
if errorlevel 1 goto :fail
"%PSQL_EXE%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%DB_USER%" -d "%DB_NAME%" -v ON_ERROR_STOP=1 -f "database\sample_data.sql"
if errorlevel 1 goto :fail
"%PSQL_EXE%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%DB_USER%" -d "%DB_NAME%" -v ON_ERROR_STOP=1 -f "database\indexes.sql"
if errorlevel 1 goto :fail

echo.
echo [4/9] Importing Transpower transmission lines...
"%PYTHON_EXE%" %PYTHON_ARGS% "scripts\import_transpower_lines.py" --insert-db --db-dsn "%DB_DSN%"
if errorlevel 1 goto :fail

echo.
echo [5/9] Importing processed weather, GIR, and recommended site data...
"%PYTHON_EXE%" %PYTHON_ARGS% "scripts\import_processed_data.py" --replace --db-dsn "%DB_DSN%"
if errorlevel 1 goto :fail

echo.
echo [6/9] Recomputing top wind and solar candidate sites...
"%PYTHON_EXE%" %PYTHON_ARGS% "scripts\site_selection_analysis.py" --insert-db --db-dsn "%DB_DSN%"
if errorlevel 1 goto :fail

echo.
echo [7/9] Setting default database search_path...
"%PSQL_EXE%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%DB_USER%" -d "%DB_NAME%" -v ON_ERROR_STOP=1 -c "ALTER DATABASE %DB_NAME% SET search_path = renewable_nz, public;"
if errorlevel 1 goto :fail

echo.
echo [8/9] Validating frontend GeoJSON files...
"%PYTHON_EXE%" %PYTHON_ARGS% "scripts\validate_geojson.py" ^
  "frontend\data\wind_suitability.geojson" ^
  "frontend\data\solar_suitability.geojson" ^
  "frontend\data\transmission_lines.geojson" ^
  "frontend\data\roads.geojson" ^
  "frontend\data\protected_areas.geojson" ^
  "frontend\data\gir_mentions.geojson" ^
  "frontend\data\weather_resource_summary.geojson" ^
  "frontend\data\site_selection_candidates.geojson"
if errorlevel 1 goto :fail

echo.
echo [9/9] Verifying database row counts...
"%PSQL_EXE%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%DB_USER%" -d "%DB_NAME%" -v ON_ERROR_STOP=1 -c "SELECT 'wind_suitability' AS layer, COUNT(*) FROM renewable_nz.wind_suitability UNION ALL SELECT 'solar_suitability', COUNT(*) FROM renewable_nz.solar_suitability UNION ALL SELECT 'transmission_lines', COUNT(*) FROM renewable_nz.transmission_lines UNION ALL SELECT 'roads', COUNT(*) FROM renewable_nz.roads UNION ALL SELECT 'protected_areas', COUNT(*) FROM renewable_nz.protected_areas UNION ALL SELECT 'gir_locations', COUNT(*) FROM renewable_nz.gir_locations UNION ALL SELECT 'weather_resource_summary', COUNT(*) FROM renewable_nz.weather_resource_summary UNION ALL SELECT 'site_selection_candidates', COUNT(*) FROM renewable_nz.site_selection_candidates ORDER BY layer;"
if errorlevel 1 goto :fail

echo.
echo [optional] Checking GeoServer availability...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri '%GEOSERVER_URL%/web/' -TimeoutSec 4 -UseBasicParsing; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo GeoServer is not running at %GEOSERVER_URL%. Skipping automatic WMS setup.
  echo Start GeoServer first, then run configure_geoserver_windows.bat.
) else (
  echo GeoServer detected. Configuring workspace, store, styles, and layers...
  "%PYTHON_EXE%" %PYTHON_ARGS% "scripts\configure_geoserver.py" --geoserver-url "%GEOSERVER_URL%" --geoserver-user "%GEOSERVER_USER%" --geoserver-password "%GEOSERVER_PASSWORD%" --postgis-host "%DB_HOST%" --postgis-port "%DB_PORT%" --postgis-db "%DB_NAME%" --postgis-user "%DB_USER%" --postgis-password "%POSTGRES_PASSWORD%" --wait-attempts 3
  if errorlevel 1 echo GeoServer auto-configuration failed. You can still configure it manually using geoserver\workspace_config.md.
)

echo.
echo Starting frontend server in a new window...
start "NZ Renewable Frontend" cmd /k ""%PYTHON_EXE%" %PYTHON_ARGS% -m http.server %FRONTEND_PORT% -d frontend"
start "" "http://localhost:%FRONTEND_PORT%/"

echo.
echo Deployment completed.
echo Frontend: http://localhost:%FRONTEND_PORT%
echo Database test: "%PSQL_EXE%" -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME%
echo.
pause
exit /b 0

:find_python
set "PYTHON_EXE="
set "PYTHON_ARGS="
py -3 --version >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_EXE=py"
  set "PYTHON_ARGS=-3"
  for /f "tokens=*" %%V in ('py -3 --version 2^>^&1') do echo Python: %%V
  exit /b 0
)
for /f "delims=" %%P in ('where python 2^>nul') do (
  set "PYTHON_EXE=%%P"
  set "PYTHON_ARGS="
  for /f "tokens=*" %%V in ('"%%P" --version 2^>^&1') do echo Python: %%V
  exit /b 0
)
echo ERROR: Python was not found. Install Python 3.12+ or make sure the py launcher is available.
exit /b 1

:find_psql
set "PSQL_EXE="
if not "%PSQL_PATH%"=="" if exist "%PSQL_PATH%" set "PSQL_EXE=%PSQL_PATH%"
if not "%PSQL_EXE%"=="" goto :psql_found
for /f "delims=" %%P in ('where psql 2^>nul') do (
  set "PSQL_EXE=%%P"
  goto :psql_found
)
for %%V in (18 17 16 15 14 13) do (
  if exist "%ProgramFiles%\PostgreSQL\%%V\bin\psql.exe" (
    set "PSQL_EXE=%ProgramFiles%\PostgreSQL\%%V\bin\psql.exe"
    goto :psql_found
  )
  if exist "%ProgramFiles(x86)%\PostgreSQL\%%V\bin\psql.exe" (
    set "PSQL_EXE=%ProgramFiles(x86)%\PostgreSQL\%%V\bin\psql.exe"
    goto :psql_found
  )
)
echo ERROR: psql.exe was not found. Set PSQL_PATH to the full path of psql.exe and run again.
echo Example: set PSQL_PATH=C:\Program Files\PostgreSQL\18\bin\psql.exe
exit /b 1

:psql_found
echo psql: %PSQL_EXE%
exit /b 0

:fail
echo.
echo Deployment failed. Read the error above, fix it, and run deploy_windows_vm.bat again.
pause
exit /b 1
