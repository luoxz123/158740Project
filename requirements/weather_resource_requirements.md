# Weather Resource Requirements

## Objective

Collect historical wind and solar resource variables for New Zealand locations to support wind farm and solar farm suitability analysis.

## Workflow

1. Read target locations from `data/raw/weather_locations_extended.csv`.
2. Download hourly historical weather variables from an open weather or climate data source.
3. Calculate summary metrics for wind and solar resource potential.
4. Export hourly CSV, summary CSV, and GeoJSON.
5. Insert summary points into PostGIS table `renewable_nz.weather_resource_summary`.
6. Display weather resource points in the Leaflet frontend.

For NIWA / Earth Sciences NZ VCSN data, import daily CSV files with `scripts/vcsn_pipeline.py`.

## Required Variables

- Wind speed at 10 m.
- Wind speed at 100 m.
- Wind gusts at 10 m.
- Sunshine duration.
- Shortwave solar radiation.
- VCSN `WindSpeed` daily mean wind speed at 10 m.
- VCSN `Radiation` daily accumulated global solar radiation.

## Location Coverage

The default location file should include rural, coastal, and inland analysis points, not only large cities, because wind farm and solar farm sites are usually outside urban centres.

## Output Format

- CSV for tabular analysis.
- GeoJSON FeatureCollection for frontend display.
- PostGIS point geometry in EPSG:2193.
