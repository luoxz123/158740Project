-- =====================================================
-- EXPORT POSTGIS LAYERS TO FRONTEND GEOJSON
-- Run with psql from project root.
-- =====================================================

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'wind_suitability',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(w) - 'geom'
            )
        )
    )
    FROM renewable_nz.wind_suitability w
) TO 'frontend/data/wind_suitability.geojson';

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'solar_suitability',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(s) - 'geom'
            )
        )
    )
    FROM renewable_nz.solar_suitability s
) TO 'frontend/data/solar_suitability.geojson';

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'transmission_lines',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(t) - 'geom'
            )
        )
    )
    FROM renewable_nz.transmission_lines t
) TO 'frontend/data/transmission_lines.geojson';

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'roads',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(r) - 'geom'
            )
        )
    )
    FROM renewable_nz.roads r
) TO 'frontend/data/roads.geojson';

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'protected_areas',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(p) - 'geom'
            )
        )
    )
    FROM renewable_nz.protected_areas p
) TO 'frontend/data/protected_areas.geojson';

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'gir_mentions',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(g) - 'geom'
            )
        )
    )
    FROM renewable_nz.gir_locations g
) TO 'frontend/data/gir_mentions.geojson';

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'weather_resource_summary',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(w) - 'geom'
            )
        )
    )
    FROM renewable_nz.weather_resource_summary w
) TO 'frontend/data/weather_resource_summary.geojson';

\copy (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'name', 'site_selection_candidates',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', to_jsonb(c) - 'geom'
            )
        )
    )
    FROM renewable_nz.site_selection_candidates c
) TO 'frontend/data/site_selection_candidates.geojson';
