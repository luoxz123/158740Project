-- =====================================================
-- POSTGIS INDEXES AND ANALYZE
-- NZ Renewable Energy Suitability Explorer
-- =====================================================

SET search_path = renewable_nz, public;

CREATE INDEX IF NOT EXISTS wind_suitability_geom_gix
    ON wind_suitability USING GIST (geom);

CREATE INDEX IF NOT EXISTS solar_suitability_geom_gix
    ON solar_suitability USING GIST (geom);

CREATE INDEX IF NOT EXISTS transmission_lines_geom_gix
    ON transmission_lines USING GIST (geom);

CREATE INDEX IF NOT EXISTS roads_geom_gix
    ON roads USING GIST (geom);

CREATE INDEX IF NOT EXISTS protected_areas_geom_gix
    ON protected_areas USING GIST (geom);

CREATE INDEX IF NOT EXISTS gir_locations_geom_gix
    ON gir_locations USING GIST (geom);

CREATE INDEX IF NOT EXISTS weather_resource_summary_geom_gix
    ON weather_resource_summary USING GIST (geom);

CREATE INDEX IF NOT EXISTS site_selection_candidates_geom_gix
    ON site_selection_candidates USING GIST (geom);

CREATE INDEX IF NOT EXISTS wind_suitability_score_idx
    ON wind_suitability (suitability_score DESC);

CREATE INDEX IF NOT EXISTS solar_suitability_score_idx
    ON solar_suitability (suitability_score DESC);

CREATE INDEX IF NOT EXISTS gir_locations_energy_type_idx
    ON gir_locations (energy_type);

CREATE INDEX IF NOT EXISTS weather_resource_summary_wind_idx
    ON weather_resource_summary (wind_resource_score DESC);

CREATE INDEX IF NOT EXISTS weather_resource_summary_solar_idx
    ON weather_resource_summary (solar_resource_score DESC);

CREATE INDEX IF NOT EXISTS site_selection_candidates_score_idx
    ON site_selection_candidates (energy_type, final_score DESC);

ANALYZE wind_suitability;
ANALYZE solar_suitability;
ANALYZE transmission_lines;
ANALYZE roads;
ANALYZE protected_areas;
ANALYZE gir_locations;
ANALYZE weather_resource_summary;
ANALYZE site_selection_candidates;
