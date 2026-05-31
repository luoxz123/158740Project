-- =====================================================
-- NON-DESTRUCTIVE UPDATE FOR ASSIGNMENT REQUIREMENT GAPS
-- Adds final candidate-site table and Wellington grid corridor.
-- Run after the original schema/sample data on an existing VM database.
-- =====================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS renewable_nz;
SET search_path = renewable_nz, public;

CREATE TABLE IF NOT EXISTS site_selection_candidates (
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

CREATE INDEX IF NOT EXISTS site_selection_candidates_geom_gix
    ON site_selection_candidates USING GIST (geom);

CREATE INDEX IF NOT EXISTS site_selection_candidates_score_idx
    ON site_selection_candidates (energy_type, final_score DESC);

INSERT INTO transmission_lines (
    line_name,
    voltage_kv,
    operator_name,
    data_source,
    geom
)
SELECT
    'Lower North Island Wellington Grid Corridor',
    220,
    'Transpower',
    'Sample network layer',
    ST_Multi(ST_Transform(ST_GeomFromText('LINESTRING(175.7 -40.4, 175.45 -40.78, 175.18 -41.02, 174.95 -41.15, 174.78 -41.22, 174.7 -41.23)', 4326), 2193))
WHERE NOT EXISTS (
    SELECT 1
    FROM transmission_lines
    WHERE line_name = 'Lower North Island Wellington Grid Corridor'
);

ANALYZE transmission_lines;
ANALYZE site_selection_candidates;
