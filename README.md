# NZ Renewable Energy Suitability Explorer

A postgraduate WebGIS platform for exploring renewable energy infrastructure suitability in New Zealand. The project combines Leaflet, Chart.js, GeoServer WMS, PostgreSQL/PostGIS, Geographic Information Retrieval (GIR), and historical weather resource analysis.

## Project Contents

- `frontend/` - Leaflet WebGIS interface with local GeoJSON fallback data and GeoServer WMS hooks.
- `database/` - PostGIS schema, sample data, indexes, import notes, and spatial queries.
- `geoserver/` - SLD styles and layer publishing guidance.
- `scripts/` - GIR scraping, NER, geocoding, historical weather collection, GeoJSON validation, and data preparation scripts.
- `backend/` - Optional lightweight API bridge for PostGIS summaries.
- `doc/` - Architecture, report, testing, and presentation materials.
- `requirements/` and `prompts/` - Project specifications and AI generation prompts.

## Quick Start

From the project root:

```powershell
cd frontend
python -m http.server 8000
```

Open:

```text
http://localhost:8000
```

The frontend works immediately with local sample GeoJSON files. If GeoServer is running, publish the PostGIS layers using the workspace and layer names in `geoserver/workspace_config.md`, then enable WMS layers in the interface.

## Recommended Windows VM Deployment

Use this option for the course VM because it reuses the installed PostgreSQL/PostGIS database and avoids Docker memory overhead.

Prerequisites on the VM:

- Python 3.12+ or the Windows `py` launcher
- PostgreSQL/PostGIS already installed
- Database `renewable_nz` already created
- Optional: GeoServer running at `http://localhost:8080/geoserver`

Run from the project root:

```bat
deploy_windows_vm.bat
```

The batch file rebuilds the `renewable_nz` schema, imports processed weather/GIR/site-selection data, validates frontend GeoJSON, and starts the frontend at:

```text
http://localhost:8000
```

Default database password is `Postgres123`. Override it before running if needed:

```bat
set POSTGRES_PASSWORD=YourPassword
deploy_windows_vm.bat
```

Detailed notes are in `doc/deployment/windows_vm_traditional.md`.

The deployment also imports the Transpower Open Data transmission line layer from `data/raw/transpower_transmission_lines.geojson` and recomputes candidate sites against that network.

## Docker VM Deployment

Docker deployment is optional. Use it only on a VM with enough memory. The repository includes a Docker Compose deployment that starts PostGIS, imports the processed project outputs, starts GeoServer, configures WMS layers, and serves the Leaflet frontend through Nginx.

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

Use `admin / geoserver` for the default GeoServer login. Docker PostGIS is exposed on host port `15432` to avoid conflicting with an existing VM PostgreSQL service:

```powershell
psql -h localhost -p 15432 -U postgres -d renewable_nz
```

More details are in `docker/README.md`.

## Database Setup

Create a database named `renewable_nz`, then run:

```powershell
psql -U postgres -d renewable_nz -f database/schema.sql
psql -U postgres -d renewable_nz -f database/sample_data.sql
psql -U postgres -d renewable_nz -f database/indexes.sql
```

All PostGIS geometry columns use EPSG:2193 (NZTM2000).

## Data Collection Pipelines

The project uses two separate collection methods:

- Web text GIR: `scripts/gir_pipeline.py` discovers or reads renewable-energy-related pages, extracts NZ place names, geocodes them, and writes `gir_locations`.
- Historical weather resources: `scripts/weather_history_pipeline.py` downloads wind speed, gust, sunshine, and solar radiation variables for rural/coastal analysis points, then writes `weather_resource_summary`.

Install Python dependencies:

```powershell
py -m pip install -r requirements.txt
py -m spacy download en_core_web_sm
```

Run both collection methods and insert into PostGIS:

```powershell
py scripts\collect_project_data.py --gir-auto-discover --gir-offline-geocode --gir-max-pages-per-site 80 --weather-start-date 2024-01-01 --weather-end-date 2024-12-31 --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

Run only the GIR pipeline:

```powershell
py scripts\gir_pipeline.py --auto-discover --offline-geocode --frontend-output frontend\data\gir_mentions.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

Run only the weather resource pipeline:

```powershell
py scripts\weather_history_pipeline.py --start-date 2024-01-01 --end-date 2024-12-31 --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

The weather pipeline uses `data/raw/weather_locations_extended.csv` by default. For a quick smoke test, add `--max-locations 5`; for the original city-only sample, add `--city-sample`.

Import NIWA / Earth Sciences NZ VCSN CSV data:

```powershell
py scripts\vcsn_pipeline.py --input data\raw\vcsn --summary-output data\processed\vcsn_weather_resource_summary.csv --geojson-output frontend\data\weather_resource_summary.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=YOUR_PASSWORD"
```

Bulk-download ordered DataHub files through the API:

```powershell
set NIWA_CUSTOMER_ID=your_customer_id
set NIWA_API_KEY=your_api_key
py scripts\vcsn_pipeline.py --download-all-datahub-files --datahub-name-contains vcsn --download-only
```

Rank the top wind and solar farm candidate sites from the existing 87-point dataset:

```powershell
py scripts\site_selection_analysis.py
```

This creates `frontend/data/site_selection_candidates.geojson`, which appears in the map as the `Recommended sites` layer.

## Data Sources To Replace Sample Data

Recommended open data sources for the final version:

- LINZ Data Service for roads, administrative boundaries, and transmission-adjacent basemap layers.
- Stats NZ Datafinder for regional boundaries and census context.
- NIWA for climate and wind/solar resource context.
- OpenStreetMap for roads and points of interest where appropriate.

Sample data is intentionally small and is included for development, demonstration, and integration testing.
