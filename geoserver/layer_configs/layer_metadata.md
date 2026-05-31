# Layer Metadata

## wind_suitability

- Purpose: Shows candidate wind farm zones generated from suitability analysis.
- Geometry: MultiPolygon
- CRS: EPSG:2193
- Key attributes: `region_name`, `suitability_score`, `avg_wind_speed`, `distance_to_grid_km`, `slope_degree`, `constraint_level`

## solar_suitability

- Purpose: Shows candidate solar farm zones generated from suitability analysis.
- Geometry: MultiPolygon
- CRS: EPSG:2193
- Key attributes: `region_name`, `suitability_score`, `solar_irradiance_kwh_m2`, `distance_to_grid_km`, `slope_degree`, `constraint_level`

## transmission_lines

- Purpose: Shows grid proximity and connection opportunities.
- Geometry: MultiLineString
- CRS: EPSG:2193
- Key attributes: `line_name`, `voltage_kv`, `operator_name`

## protected_areas

- Purpose: Shows environmental constraints that should be avoided or carefully assessed.
- Geometry: MultiPolygon
- CRS: EPSG:2193
- Key attributes: `area_name`, `protection_status`, `constraint_level`

## gir_locations

- Purpose: Shows renewable-energy-related locations extracted from news or web text.
- Geometry: Point
- CRS: EPSG:2193
- Key attributes: `article_title`, `place_name`, `energy_type`, `source_url`, `confidence`
