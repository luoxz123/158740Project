-- =====================================================
-- WEATHER RESOURCE ANALYSIS QUERIES
-- NZ Renewable Energy Suitability Explorer
-- =====================================================

SET search_path = renewable_nz, public;

-- 1. Rank locations by wind resource at 100 m.
SELECT
    place_name,
    region,
    mean_wind_speed_100m_ms,
    p90_wind_speed_100m_ms,
    wind_resource_score
FROM weather_resource_summary
ORDER BY wind_resource_score DESC, mean_wind_speed_100m_ms DESC;

-- 2. Rank locations by solar resource.
SELECT
    place_name,
    region,
    total_sunshine_hours,
    total_shortwave_radiation_kwh_m2,
    solar_resource_score
FROM weather_resource_summary
ORDER BY solar_resource_score DESC, total_shortwave_radiation_kwh_m2 DESC;

-- 3. Find weather resource points near existing suitability polygons.
SELECT
    w.place_name,
    s.energy_type,
    s.region_name,
    s.suitability_score,
    ROUND((ST_Distance(w.geom, s.geom) / 1000.0)::numeric, 2) AS distance_km
FROM weather_resource_summary w
CROSS JOIN LATERAL (
    SELECT *
    FROM suitability_all s
    ORDER BY w.geom <-> s.geom
    LIMIT 1
) s
ORDER BY distance_km;

-- 4. Combined simple weather resource suitability.
SELECT
    place_name,
    region,
    wind_resource_score,
    solar_resource_score,
    ROUND(((wind_resource_score + solar_resource_score) / 2.0)::numeric, 1) AS combined_weather_score
FROM weather_resource_summary
ORDER BY combined_weather_score DESC;
