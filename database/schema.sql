-- =====================================================
-- POSTGIS SCHEMA
-- NZ Renewable Energy Suitability Explorer
-- Geometry CRS: EPSG:2193 NZTM2000
-- =====================================================

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS renewable_nz;
SET search_path = renewable_nz, public;

DROP TABLE IF EXISTS gir_locations CASCADE;
DROP TABLE IF EXISTS site_selection_candidates CASCADE;
DROP TABLE IF EXISTS weather_resource_summary CASCADE;
DROP TABLE IF EXISTS protected_areas CASCADE;
DROP TABLE IF EXISTS roads CASCADE;
DROP TABLE IF EXISTS transmission_lines CASCADE;
DROP TABLE IF EXISTS solar_suitability CASCADE;
DROP TABLE IF EXISTS wind_suitability CASCADE;

CREATE TABLE wind_suitability (
    id SERIAL PRIMARY KEY,
    region_name VARCHAR(120) NOT NULL,
    suitability_score INTEGER NOT NULL CHECK (suitability_score BETWEEN 0 AND 100),
    avg_wind_speed NUMERIC(5,2),
    distance_to_grid_km NUMERIC(6,2),
    slope_degree NUMERIC(5,2),
    constraint_level VARCHAR(30) NOT NULL DEFAULT 'Medium',
    data_source VARCHAR(150) NOT NULL DEFAULT 'Sample GIS analysis',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    geom geometry(MULTIPOLYGON, 2193) NOT NULL,
    CONSTRAINT wind_geom_valid CHECK (ST_IsValid(geom))
);

CREATE TABLE solar_suitability (
    id SERIAL PRIMARY KEY,
    region_name VARCHAR(120) NOT NULL,
    suitability_score INTEGER NOT NULL CHECK (suitability_score BETWEEN 0 AND 100),
    solar_irradiance_kwh_m2 NUMERIC(5,2),
    distance_to_grid_km NUMERIC(6,2),
    slope_degree NUMERIC(5,2),
    constraint_level VARCHAR(30) NOT NULL DEFAULT 'Medium',
    data_source VARCHAR(150) NOT NULL DEFAULT 'Sample GIS analysis',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    geom geometry(MULTIPOLYGON, 2193) NOT NULL,
    CONSTRAINT solar_geom_valid CHECK (ST_IsValid(geom))
);

CREATE TABLE transmission_lines (
    id SERIAL PRIMARY KEY,
    line_name VARCHAR(140) NOT NULL,
    voltage_kv INTEGER,
    operator_name VARCHAR(100) NOT NULL DEFAULT 'Transpower',
    data_source VARCHAR(150) NOT NULL DEFAULT 'Sample network layer',
    geom geometry(MULTILINESTRING, 2193) NOT NULL,
    CONSTRAINT transmission_geom_valid CHECK (ST_IsValid(geom))
);

CREATE TABLE roads (
    id SERIAL PRIMARY KEY,
    road_name VARCHAR(140),
    road_class VARCHAR(60),
    data_source VARCHAR(150) NOT NULL DEFAULT 'Sample access layer',
    geom geometry(MULTILINESTRING, 2193) NOT NULL,
    CONSTRAINT roads_geom_valid CHECK (ST_IsValid(geom))
);

CREATE TABLE protected_areas (
    id SERIAL PRIMARY KEY,
    area_name VARCHAR(140) NOT NULL,
    protection_status VARCHAR(80) NOT NULL DEFAULT 'Protected',
    constraint_level VARCHAR(30) NOT NULL DEFAULT 'High',
    data_source VARCHAR(150) NOT NULL DEFAULT 'Sample environmental constraint',
    geom geometry(MULTIPOLYGON, 2193) NOT NULL,
    CONSTRAINT protected_geom_valid CHECK (ST_IsValid(geom))
);

CREATE TABLE gir_locations (
    id SERIAL PRIMARY KEY,
    article_title TEXT NOT NULL,
    place_name VARCHAR(140) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    energy_type VARCHAR(30) NOT NULL CHECK (energy_type IN ('wind', 'solar', 'mixed', 'renewable')),
    source_url TEXT,
    confidence NUMERIC(4,3),
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    geom geometry(POINT, 2193) NOT NULL,
    CONSTRAINT gir_geom_valid CHECK (ST_IsValid(geom))
);

CREATE TABLE weather_resource_summary (
    id SERIAL PRIMARY KEY,
    place_name VARCHAR(140) NOT NULL,
    region VARCHAR(140),
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    hour_count INTEGER NOT NULL,
    mean_wind_speed_10m_ms NUMERIC(8,3),
    mean_wind_speed_100m_ms NUMERIC(8,3),
    p90_wind_speed_100m_ms NUMERIC(8,3),
    max_wind_gust_10m_ms NUMERIC(8,3),
    mean_shortwave_radiation_wm2 NUMERIC(10,3),
    total_shortwave_radiation_kwh_m2 NUMERIC(12,3),
    total_sunshine_hours NUMERIC(12,2),
    wind_resource_score NUMERIC(5,1),
    solar_resource_score NUMERIC(5,1),
    data_source TEXT NOT NULL DEFAULT 'Open-Meteo Historical Weather API',
    geom geometry(POINT, 2193) NOT NULL,
    UNIQUE (place_name, start_date, end_date),
    CONSTRAINT weather_resource_geom_valid CHECK (ST_IsValid(geom))
);

CREATE TABLE site_selection_candidates (
    id SERIAL PRIMARY KEY,
    rank INTEGER NOT NULL,
    energy_type VARCHAR(20) NOT NULL CHECK (energy_type IN ('wind', 'solar')),
    candidate_name VARCHAR(220) NOT NULL,
    region VARCHAR(160),
    final_score NUMERIC(5,1),
    weather_resource_score NUMERIC(5,1),
    grid_connection_score NUMERIC(5,1),
    gir_evidence_score NUMERIC(5,1),
    interpolation_confidence NUMERIC(5,1),
    distance_to_transmission_km NUMERIC(8,2),
    mean_wind_speed_100m_ms NUMERIC(8,3),
    p90_wind_speed_100m_ms NUMERIC(8,3),
    total_shortwave_radiation_kwh_m2 NUMERIC(12,3),
    total_sunshine_hours NUMERIC(12,2),
    nearest_weather_point VARCHAR(160),
    gir_mentions_nearby INTEGER,
    candidate_source VARCHAR(40),
    score_formula TEXT,
    geom geometry(POINT, 2193) NOT NULL,
    UNIQUE (energy_type, rank),
    CONSTRAINT site_selection_geom_valid CHECK (ST_IsValid(geom))
);

CREATE OR REPLACE VIEW suitability_all AS
SELECT
    'wind'::text AS energy_type,
    id,
    region_name,
    suitability_score,
    distance_to_grid_km,
    slope_degree,
    constraint_level,
    geom
FROM wind_suitability
UNION ALL
SELECT
    'solar'::text AS energy_type,
    id,
    region_name,
    suitability_score,
    distance_to_grid_km,
    slope_degree,
    constraint_level,
    geom
FROM solar_suitability;

CREATE OR REPLACE VIEW suitability_web_mercator AS
SELECT
    energy_type,
    id,
    region_name,
    suitability_score,
    distance_to_grid_km,
    slope_degree,
    constraint_level,
    ST_Transform(geom, 3857)::geometry(MULTIPOLYGON, 3857) AS geom
FROM suitability_all;

COMMENT ON TABLE wind_suitability IS 'Wind farm suitability zones generated from GIS multi-criteria analysis.';
COMMENT ON TABLE solar_suitability IS 'Solar farm suitability zones generated from GIS multi-criteria analysis.';
COMMENT ON TABLE gir_locations IS 'Point layer created by the GIR pipeline from renewable energy articles.';
COMMENT ON TABLE weather_resource_summary IS 'Point layer created from historical wind and solar weather resource variables.';
COMMENT ON TABLE site_selection_candidates IS 'Top wind and solar candidate sites ranked using weather resource interpolation, grid proximity, and GIR evidence.';
