# Data Collection Strategy

The project uses two collection methods because the evidence types are different.

## Method 1: Web Text GIR

Purpose:

- Collect public text about renewable energy, wind, solar, and related weather or infrastructure issues.
- Extract New Zealand place names from the text.
- Convert extracted place names into a spatial point layer.

Implementation:

- Script: `scripts/gir_pipeline.py`
- Main outputs:
  - `data/processed/renewable_energy_mentions.geojson`
  - `frontend/data/gir_mentions.geojson`
  - PostGIS table `renewable_nz.gir_locations`

Recommended VM command:

```powershell
py scripts\gir_pipeline.py --auto-discover --offline-geocode --max-pages-per-site 80 --frontend-output frontend\data\gir_mentions.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

Optional Facebook text should be manually exported to `data/raw/facebook_mentions.csv` or obtained through approved Meta API access, then added with `--include-facebook-csv`.

## Method 2: Historical Weather Resource Data

Purpose:

- Collect structured wind and solar resource variables for suitability analysis.
- Summarise wind speed, gusts, sunshine hours, and solar radiation by location.
- Support wind farm and solar farm resource scoring.

Implementation:

- Script: `scripts/weather_history_pipeline.py`
- Default locations: `data/raw/weather_locations_extended.csv`
- NIWA VCSN importer: `scripts/vcsn_pipeline.py`
- Main outputs:
  - `data/processed/weather_hourly_history.csv`
  - `data/processed/weather_resource_summary.csv`
  - `frontend/data/weather_resource_summary.geojson`
  - PostGIS table `renewable_nz.weather_resource_summary`

Recommended VM command:

```powershell
py scripts\weather_history_pipeline.py --start-date 2024-01-01 --end-date 2024-12-31 --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

Quick test:

```powershell
py scripts\weather_history_pipeline.py --max-locations 5
```

NIWA / Earth Sciences NZ VCSN import:

```powershell
py scripts\vcsn_pipeline.py --input data\raw\vcsn --geojson-output frontend\data\weather_resource_summary.geojson --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

## Combined VM Command

Run both methods with one command:

```powershell
py scripts\collect_project_data.py --gir-auto-discover --gir-offline-geocode --gir-max-pages-per-site 80 --weather-start-date 2024-01-01 --weather-end-date 2024-12-31 --insert-db --db-dsn "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123"
```

## Why The Methods Are Separate

GIR is for unstructured web text and public place mentions. Weather resource data is structured time-series evidence. Combining them into one scraper would make the project less reliable and less defensible. Keeping them separate gives the WebGIS two evidence layers: social/textual geographic evidence and physical resource evidence.

## Site Selection Screening

Because paid VCSN bulk downloads are not suitable for the student project budget, final site screening can use the already collected 87-point weather resource dataset:

```powershell
py scripts\site_selection_analysis.py
```

The script interpolates weather resources, combines transmission distance and GIR evidence, and outputs the top 10 wind farm and top 10 solar farm candidates.
