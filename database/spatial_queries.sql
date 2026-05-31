-- =====================================================
-- SAMPLE SPATIAL QUERIES
-- NZ Renewable Energy Suitability Explorer
-- =====================================================

SET search_path = renewable_nz, public;

-- 1. Validate CRS consistency.
SELECT
    f_table_name,
    f_geometry_column,
    srid,
    type
FROM geometry_columns
WHERE f_table_schema = 'renewable_nz'
ORDER BY f_table_name;

-- 2. Find highly suitable zones within 10 km of transmission lines.
SELECT
    s.energy_type,
    s.region_name,
    s.suitability_score,
    ROUND((MIN(ST_Distance(s.geom, t.geom)) / 1000.0)::numeric, 2) AS nearest_grid_km
FROM suitability_all s
JOIN transmission_lines t
    ON ST_DWithin(s.geom, t.geom, 10000)
WHERE s.suitability_score >= 75
GROUP BY s.energy_type, s.region_name, s.suitability_score
ORDER BY s.suitability_score DESC;

-- 3. Exclude zones intersecting protected areas.
SELECT
    s.energy_type,
    s.region_name,
    s.suitability_score
FROM suitability_all s
WHERE NOT EXISTS (
    SELECT 1
    FROM protected_areas p
    WHERE ST_Intersects(s.geom, p.geom)
)
ORDER BY s.suitability_score DESC;

-- 4. Summarise suitability by energy type.
SELECT
    energy_type,
    COUNT(*) AS zone_count,
    ROUND(AVG(suitability_score), 1) AS avg_score,
    MAX(suitability_score) AS top_score
FROM suitability_all
GROUP BY energy_type
ORDER BY avg_score DESC;

-- 5. Link GIR mentions to nearest suitability zone.
SELECT
    g.place_name,
    g.energy_type AS mention_type,
    s.energy_type AS nearest_zone_type,
    s.region_name,
    ROUND((ST_Distance(g.geom, s.geom) / 1000.0)::numeric, 2) AS distance_km
FROM gir_locations g
CROSS JOIN LATERAL (
    SELECT *
    FROM suitability_all s
    ORDER BY g.geom <-> s.geom
    LIMIT 1
) s
ORDER BY distance_km;

-- 6. Export filtered zones as GeoJSON in WGS84 for web use.
SELECT jsonb_build_object(
    'type', 'FeatureCollection',
    'features', jsonb_agg(
        jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
            'properties', to_jsonb(row) - 'geom'
        )
    )
) AS geojson
FROM (
    SELECT
        energy_type,
        id,
        region_name,
        suitability_score,
        distance_to_grid_km,
        slope_degree,
        constraint_level,
        geom
    FROM suitability_all
    WHERE suitability_score >= 70
) row;

-- 7. Detect invalid or empty geometries before publishing to GeoServer.
SELECT 'wind_suitability' AS table_name, id, ST_IsValidReason(geom) AS reason
FROM wind_suitability
WHERE NOT ST_IsValid(geom) OR ST_IsEmpty(geom)
UNION ALL
SELECT 'solar_suitability', id, ST_IsValidReason(geom)
FROM solar_suitability
WHERE NOT ST_IsValid(geom) OR ST_IsEmpty(geom)
UNION ALL
SELECT 'protected_areas', id, ST_IsValidReason(geom)
FROM protected_areas
WHERE NOT ST_IsValid(geom) OR ST_IsEmpty(geom);

-- 8. Review final recommended wind and solar sites.
SELECT
    energy_type,
    rank,
    candidate_name,
    region,
    final_score,
    weather_resource_score,
    grid_connection_score,
    gir_evidence_score,
    distance_to_transmission_km
FROM site_selection_candidates
ORDER BY energy_type, rank;

-- 9. Find recommended sites close to protected areas for follow-up screening.
SELECT
    c.energy_type,
    c.rank,
    c.candidate_name,
    p.area_name,
    ROUND((ST_Distance(c.geom, p.geom) / 1000.0)::numeric, 2) AS distance_km
FROM site_selection_candidates c
CROSS JOIN LATERAL (
    SELECT *
    FROM protected_areas p
    ORDER BY c.geom <-> p.geom
    LIMIT 1
) p
ORDER BY distance_km;
