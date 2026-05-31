# GitHub Upload Checklist

Use this checklist before uploading the project to GitHub and cloning it on the VM.

## Files To Keep

Keep these deployment-critical files:

- `deploy_windows_vm.bat`
- `start_frontend_windows.bat`
- `configure_geoserver_windows.bat`
- `database/*.sql`
- `frontend/`
- `geoserver/`
- `scripts/`
- `data/processed/weather_resource_summary.csv`
- `data/processed/renewable_energy_mentions.geojson`
- `frontend/data/*.geojson`
- `requirements.txt`
- `README.md`
- `doc/`

## Files Not To Upload

The `.gitignore` already excludes these:

- `API.txt`
- `.env`
- `*.log`
- `data/processed/weather_hourly_history.csv`
- `data/processed/cache/`
- Python virtual environments
- GIS binary exports such as shapefiles, GeoPackages, TIFFs, and ZIPs

`weather_hourly_history.csv` is about 118 MB and is not needed for deployment because the project uses the processed summary CSV and GeoJSON outputs.

## Push From Your Main Machine

```bat
git init
git add .
git commit -m "Initial renewable WebGIS project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

Before committing, check ignored files:

```bat
git status --ignored
```

## Deploy On The VM

```bat
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
deploy_windows_vm.bat
```

If PostgreSQL uses a different password:

```bat
set POSTGRES_PASSWORD=YourPassword
deploy_windows_vm.bat
```

If `psql.exe` is not detected:

```bat
set PSQL_PATH=C:\Program Files\PostgreSQL\18\bin\psql.exe
deploy_windows_vm.bat
```

After deployment:

```text
Frontend: http://localhost:8000
GeoServer: http://localhost:8080/geoserver
```
