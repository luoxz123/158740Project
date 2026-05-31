# Testing Plan

## Frontend Tests

- Confirm the map loads at desktop and mobile widths.
- Toggle each local GeoJSON layer.
- Enable and disable the heatmap.
- Search for `Taranaki`, `Marlborough`, `Canterbury`, `Makara`, `State highway`, and `solar`.
- Change the energy type filter and minimum suitability score.
- Confirm popup attributes and popup charts appear.
- Export visible GeoJSON and confirm it is valid JSON.

## GeoServer Tests

- Confirm each WMS layer opens in GeoServer Layer Preview.
- Confirm the frontend WMS switch displays published layers.
- Confirm GeoServer can reproject EPSG:2193 layers to web map output.
- Confirm SLD styles are assigned to the correct layers.

## PostGIS Tests

- Run `database/spatial_queries.sql`.
- Confirm all geometry columns use EPSG:2193.
- Confirm GiST indexes exist.
- Confirm no invalid or empty geometry rows are returned.

## GIR Tests

- Run `python scripts/gir_pipeline.py --offline-sample`.
- Run `python scripts/validate_geojson.py data/processed/renewable_energy_mentions.geojson`.
- Confirm generated GIR points display in Leaflet.
- Confirm extracted places include New Zealand locations relevant to the articles.

## Site Selection Tests

- Run `py scripts\site_selection_analysis.py`.
- Confirm `wind_farm_candidates_top10.csv` ranks Makara and Ohariu Valley highly after the Wellington transmission corridor correction.
- Confirm `solar_farm_candidates_top10.csv` contains 10 solar candidates.
- Validate `frontend/data/site_selection_candidates.geojson`.
- Confirm the `Recommended sites` layer displays and popups show rank, final score, resource score, grid distance, and GIR evidence.

## Responsiveness

- Test at 1366 x 768 desktop.
- Test at 390 x 844 mobile.
- Confirm controls remain readable and do not overlap the map legend or top bar.
