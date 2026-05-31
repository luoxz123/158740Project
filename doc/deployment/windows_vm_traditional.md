# Windows VM Traditional Deployment

Use this path when the VM does not have enough memory for Docker.

## What The One-Click Batch Does

`deploy_windows_vm.bat` performs these steps:

1. Finds Python and `psql.exe`.
2. Installs Python dependencies from `requirements.txt`.
3. Connects to the existing `renewable_nz` database.
4. Rebuilds the `renewable_nz` schema using `database/schema.sql`.
5. Loads sample suitability, road, protected area, and transmission layers.
6. Imports processed weather, GIR, and site-selection outputs.
7. Recomputes the top 10 wind and top 10 solar candidate sites.
8. Validates frontend GeoJSON files.
9. Starts the frontend at `http://localhost:8000`.
10. Configures GeoServer automatically if GeoServer is already running.

The script does not drop the whole database. It rebuilds tables inside the `renewable_nz` schema and leaves unrelated `public` tables alone.

## VM Steps

After cloning the repository on the VM:

```bat
deploy_windows_vm.bat
```

Default database settings:

```text
host=localhost
port=5432
database=renewable_nz
user=postgres
password=Postgres123
```

To override settings for one run:

```bat
set POSTGRES_PASSWORD=YourPassword
set DB_PORT=5432
deploy_windows_vm.bat
```

If `psql.exe` is not found automatically:

```bat
set PSQL_PATH=C:\Program Files\PostgreSQL\18\bin\psql.exe
deploy_windows_vm.bat
```

## GeoServer

If GeoServer is already running at `http://localhost:8080/geoserver`, the batch tries to configure it automatically.

If GeoServer is not running yet, start GeoServer first and then run:

```bat
configure_geoserver_windows.bat
```

Default GeoServer login:

```text
admin / geoserver
```

## GitHub Upload Notes

Do not upload local secrets or large generated hourly data. The `.gitignore` already excludes:

- `API.txt`
- `.env`
- `*.log`
- `data/processed/weather_hourly_history.csv`
- Python virtual environments and caches

The deployment uses `data/processed/weather_resource_summary.csv` and frontend GeoJSON files, so the large hourly CSV is not required on GitHub.

## Fresh GitHub Repository

From the project root:

```bat
git init
git add .
git commit -m "Initial renewable WebGIS project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

On the VM:

```bat
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
deploy_windows_vm.bat
```
