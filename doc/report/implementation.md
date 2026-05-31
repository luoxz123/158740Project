# Implementation

## Frontend

The frontend is implemented in `frontend/index.html`, `frontend/styles.css`, and `frontend/app.js`.

Implemented functions:

- Layer toggling for wind, solar, transmission, protected areas, GIR points, and heatmap.
- Weather resource point layer for historical wind and solar indicators.
- Suitability filtering by energy type and minimum score.
- Location search over region names, article titles, place names, and energy type.
- Popup information with a small Chart.js score graphic.
- Dashboard charts for top suitability zones and energy type distribution.
- GeoServer WMS integration switch.
- Local GeoJSON fallback layers for development and demo reliability.

## Database

The database scripts create a `renewable_nz` schema and spatial tables for suitability, constraints, GIR, and weather resources:

- `wind_suitability`
- `solar_suitability`
- `transmission_lines`
- `roads`
- `protected_areas`
- `gir_locations`
- `weather_resource_summary`

All geometry columns use EPSG:2193 and GiST indexes.

## GeoServer

GeoServer publishes the PostGIS layers as WMS. The expected workspace is `renewable_nz`, and SLD styles are stored in `geoserver/styles/`.

## GIR

The GIR pipeline is implemented in `scripts/gir_pipeline.py`. It supports offline sample mode, manual URL mode, automatic sitemap discovery, Facebook CSV import, GeoJSON export, and optional PostGIS insertion into `gir_locations`.

## Weather Resource Data

The historical weather resource pipeline is implemented in `scripts/weather_history_pipeline.py`. It downloads structured wind and solar weather variables for selected New Zealand locations, exports hourly and summary CSV files, writes a frontend GeoJSON layer, and optionally upserts records into `weather_resource_summary`.

`scripts/collect_project_data.py` can run both the GIR and weather resource pipelines in one VM command while keeping the two datasets separate.
