# Database Requirements

The database shall contain:

- `wind_suitability`
- `solar_suitability`
- `transmission_lines`
- `roads`
- `protected_areas`
- `gir_locations`
- `weather_resource_summary`
- `site_selection_candidates`

## Rules

- Use PostgreSQL and PostGIS.
- Store all geometries as EPSG:2193.
- Create spatial GiST indexes.
- Validate geometry with `ST_IsValid`.
- Provide sample spatial queries.
- Provide a GeoJSON export query for frontend use.
