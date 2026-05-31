# Docker Deployment

This folder supports a VM deployment for the NZ Renewable Energy Suitability Explorer.

## Services

- `postgis`: PostgreSQL/PostGIS database with `database/schema.sql`, `sample_data.sql`, and `indexes.sql` loaded on first start.
- `importer`: one-shot Python job that imports existing processed CSV/GeoJSON outputs into PostGIS.
- `geoserver`: GeoServer WMS server.
- `geoserver-init`: one-shot Python job that creates the GeoServer workspace, PostGIS datastore, SLD styles, and WMS layers.
- `frontend`: Nginx static web server for the Leaflet app.
- `api`: optional FastAPI service, enabled with the `api` profile.

## VM Commands

From the project root:

```powershell
copy .env.docker.example .env
docker compose up --build -d
docker compose ps
```

Open:

```text
http://localhost:8000
http://localhost:8080/geoserver
```

GeoServer login defaults:

```text
admin / geoserver
```

If you access the VM from another computer, replace `localhost` with the VM IP address.

The Docker PostGIS database is exposed on host port `15432` by default to avoid conflict with an existing PostgreSQL service on the VM:

```powershell
psql -h localhost -p 15432 -U postgres -d renewable_nz
```

## Check Logs

```powershell
docker compose logs -f importer geoserver-init
```

## Rebuild From Scratch

Use this only when you want to delete the Docker database volume and reload all SQL/data:

```powershell
docker compose down -v
docker compose up --build -d
```

## Run Pipelines Inside Docker

```powershell
docker compose run --rm importer python scripts/site_selection_analysis.py --insert-db --db-dsn "host=postgis port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

Live web scraping or weather downloads require internet access from the VM.
