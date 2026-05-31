-- =====================================================
-- SAMPLE POSTGIS DATASET
-- NZ Renewable Energy Suitability Explorer
-- Run after database/schema.sql
-- =====================================================

SET search_path = renewable_nz, public;

TRUNCATE TABLE
    site_selection_candidates,
    weather_resource_summary,
    gir_locations,
    protected_areas,
    roads,
    transmission_lines,
    solar_suitability,
    wind_suitability
RESTART IDENTITY CASCADE;

INSERT INTO wind_suitability (
    region_name,
    suitability_score,
    avg_wind_speed,
    distance_to_grid_km,
    slope_degree,
    constraint_level,
    geom
)
VALUES
(
    'Taranaki Coastal Wind Zone',
    89,
    11.4,
    3.2,
    7.5,
    'Low',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((173.78 -39.35, 174.28 -39.35, 174.28 -38.98, 173.78 -38.98, 173.78 -39.35))', 4326), 2193))
),
(
    'Manawatu Ridge Wind Zone',
    84,
    10.6,
    4.0,
    9.1,
    'Medium',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((175.36 -40.58, 175.88 -40.58, 175.88 -40.23, 175.36 -40.23, 175.36 -40.58))', 4326), 2193))
),
(
    'Canterbury Foothills Wind Zone',
    78,
    9.7,
    6.4,
    8.4,
    'Medium',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((171.55 -43.85, 172.28 -43.85, 172.28 -43.45, 171.55 -43.45, 171.55 -43.85))', 4326), 2193))
),
(
    'Southland Coastal Wind Zone',
    73,
    9.3,
    7.5,
    6.1,
    'Medium',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((168.05 -46.62, 168.72 -46.62, 168.72 -46.22, 168.05 -46.22, 168.05 -46.62))', 4326), 2193))
);

INSERT INTO solar_suitability (
    region_name,
    suitability_score,
    solar_irradiance_kwh_m2,
    distance_to_grid_km,
    slope_degree,
    constraint_level,
    geom
)
VALUES
(
    'Marlborough Solar Zone',
    91,
    4.9,
    2.8,
    3.2,
    'Low',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((173.58 -41.78, 174.12 -41.78, 174.12 -41.38, 173.58 -41.38, 173.58 -41.78))', 4326), 2193))
),
(
    'Hawke''s Bay Solar Zone',
    86,
    4.7,
    4.1,
    2.8,
    'Low',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((176.55 -39.92, 177.08 -39.92, 177.08 -39.48, 176.55 -39.48, 176.55 -39.92))', 4326), 2193))
),
(
    'Canterbury Plains Solar Zone',
    82,
    4.5,
    5.6,
    2.1,
    'Medium',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((171.95 -44.18, 172.78 -44.18, 172.78 -43.72, 171.95 -43.72, 171.95 -44.18))', 4326), 2193))
),
(
    'Central Otago Solar Zone',
    76,
    4.3,
    8.2,
    5.0,
    'Medium',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((169.35 -45.35, 170.02 -45.35, 170.02 -44.95, 169.35 -44.95, 169.35 -45.35))', 4326), 2193))
);

INSERT INTO transmission_lines (
    line_name,
    voltage_kv,
    operator_name,
    geom
)
VALUES
(
    'North Island Grid Backbone',
    220,
    'Transpower',
    ST_Multi(ST_Transform(ST_GeomFromText('LINESTRING(174.8 -36.9, 175.2 -38.1, 175.6 -39.2, 175.7 -40.4)', 4326), 2193))
),
(
    'South Island Grid Backbone',
    220,
    'Transpower',
    ST_Multi(ST_Transform(ST_GeomFromText('LINESTRING(172.6 -41.3, 172.2 -43.5, 171.0 -44.4, 169.6 -45.2, 168.6 -46.4)', 4326), 2193))
),
(
    'Lower North Island Wellington Grid Corridor',
    220,
    'Transpower',
    ST_Multi(ST_Transform(ST_GeomFromText('LINESTRING(175.7 -40.4, 175.45 -40.78, 175.18 -41.02, 174.95 -41.15, 174.78 -41.22, 174.7 -41.23)', 4326), 2193))
);

INSERT INTO roads (
    road_name,
    road_class,
    geom
)
VALUES
(
    'State Highway 1 Sample Corridor',
    'State highway',
    ST_Multi(ST_Transform(ST_GeomFromText('LINESTRING(174.78 -36.85, 175.28 -38.68, 175.62 -40.35, 172.63 -43.53, 170.50 -45.86)', 4326), 2193))
),
(
    'Canterbury Access Corridor',
    'Regional road',
    ST_Multi(ST_Transform(ST_GeomFromText('LINESTRING(171.80 -43.82, 172.20 -43.72, 172.65 -43.61)', 4326), 2193))
);

INSERT INTO protected_areas (
    area_name,
    protection_status,
    constraint_level,
    geom
)
VALUES
(
    'Tongariro National Park Buffer',
    'Protected',
    'High',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((175.28 -39.42, 176.02 -39.42, 176.02 -38.92, 175.28 -38.92, 175.28 -39.42))', 4326), 2193))
),
(
    'Aoraki Mackenzie Conservation Buffer',
    'Protected',
    'High',
    ST_Multi(ST_Transform(ST_GeomFromText('POLYGON((170.05 -44.62, 170.92 -44.62, 170.92 -43.92, 170.05 -43.92, 170.05 -44.62))', 4326), 2193))
);

INSERT INTO gir_locations (
    article_title,
    place_name,
    latitude,
    longitude,
    energy_type,
    source_url,
    confidence,
    geom
)
VALUES
(
    'Wind farm proposal discussed near Taranaki coast',
    'Taranaki',
    -39.22,
    174.08,
    'wind',
    'sample://rnz-wind-taranaki',
    0.860,
    ST_Transform(ST_SetSRID(ST_MakePoint(174.08, -39.22), 4326), 2193)
),
(
    'Solar investment expands across Marlborough',
    'Marlborough',
    -41.52,
    173.96,
    'solar',
    'sample://stuff-solar-marlborough',
    0.910,
    ST_Transform(ST_SetSRID(ST_MakePoint(173.96, -41.52), 4326), 2193)
),
(
    'Hawke''s Bay councils review renewable energy zones',
    'Hawke''s Bay',
    -39.67,
    176.87,
    'solar',
    'sample://nzherald-solar-hawkes-bay',
    0.840,
    ST_Transform(ST_SetSRID(ST_MakePoint(176.87, -39.67), 4326), 2193)
),
(
    'Canterbury communities consider wind and solar projects',
    'Canterbury',
    -43.75,
    172.25,
    'mixed',
    'sample://rnz-renewable-canterbury',
    0.800,
    ST_Transform(ST_SetSRID(ST_MakePoint(172.25, -43.75), 4326), 2193)
);
