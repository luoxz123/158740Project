@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if "%DB_HOST%"=="" set "DB_HOST=localhost"
if "%DB_PORT%"=="" set "DB_PORT=5432"
if "%DB_NAME%"=="" set "DB_NAME=renewable_nz"
if "%DB_USER%"=="" set "DB_USER=postgres"
if "%POSTGRES_PASSWORD%"=="" set "POSTGRES_PASSWORD=Postgres123"
if "%GEOSERVER_URL%"=="" set "GEOSERVER_URL=http://localhost:8080/geoserver"
if "%GEOSERVER_USER%"=="" set "GEOSERVER_USER=admin"
if "%GEOSERVER_PASSWORD%"=="" set "GEOSERVER_PASSWORD=geoserver"

py -3 --version >nul 2>nul
if not errorlevel 1 (
  py -3 scripts\configure_geoserver.py --geoserver-url "%GEOSERVER_URL%" --geoserver-user "%GEOSERVER_USER%" --geoserver-password "%GEOSERVER_PASSWORD%" --postgis-host "%DB_HOST%" --postgis-port "%DB_PORT%" --postgis-db "%DB_NAME%" --postgis-user "%DB_USER%" --postgis-password "%POSTGRES_PASSWORD%"
  pause
  exit /b %ERRORLEVEL%
)

python scripts\configure_geoserver.py --geoserver-url "%GEOSERVER_URL%" --geoserver-user "%GEOSERVER_USER%" --geoserver-password "%GEOSERVER_PASSWORD%" --postgis-host "%DB_HOST%" --postgis-port "%DB_PORT%" --postgis-db "%DB_NAME%" --postgis-user "%DB_USER%" --postgis-password "%POSTGRES_PASSWORD%"
pause
exit /b %ERRORLEVEL%
