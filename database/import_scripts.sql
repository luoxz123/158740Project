-- =====================================================
-- IMPORT NOTES FOR REAL GIS DATA
-- NZ Renewable Energy Suitability Explorer
-- =====================================================

-- Example ogr2ogr commands:
--
-- ogr2ogr -f PostgreSQL PG:"host=localhost dbname=renewable_nz user=postgres password=postgres" ^
--   data/processed/wind_suitability.gpkg ^
--   -nln renewable_nz.wind_suitability ^
--   -lco GEOMETRY_NAME=geom ^
--   -t_srs EPSG:2193 ^
--   -append
--
-- ogr2ogr -f PostgreSQL PG:"host=localhost dbname=renewable_nz user=postgres password=postgres" ^
--   data/processed/gir_locations.geojson ^
--   -nln renewable_nz.gir_locations ^
--   -lco GEOMETRY_NAME=geom ^
--   -t_srs EPSG:2193 ^
--   -append

SET search_path = renewable_nz, public;

-- Template update for imported WGS84 GIR points.
-- Use this when staging tables contain longitude and latitude columns.
--
-- UPDATE gir_locations
-- SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), 2193)
-- WHERE geom IS NULL;

-- Template geometry repair step for imported polygon layers.
--
-- UPDATE wind_suitability
-- SET geom = ST_Multi(ST_MakeValid(geom))
-- WHERE NOT ST_IsValid(geom);
