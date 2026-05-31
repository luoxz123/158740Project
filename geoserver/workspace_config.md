# GeoServer Workspace Configuration

## Workspace

Create a workspace:

```text
renewable_nz
```

Recommended namespace URI:

```text
https://massey.example/renewable_nz
```

## PostGIS Store

Create a PostGIS datastore in the `renewable_nz` workspace.

Suggested store name:

```text
postgis_renewable_nz
```

Connection parameters:

```text
host: localhost
port: 5432
database: renewable_nz
schema: renewable_nz
user: postgres
```

## Publish Layers

Publish these tables or views:

| GeoServer layer name | PostGIS source | Style |
|---|---|---|
| `renewable_nz:wind_suitability` | `renewable_nz.wind_suitability` | `wind_style` |
| `renewable_nz:solar_suitability` | `renewable_nz.solar_suitability` | `solar_style` |
| `renewable_nz:transmission_lines` | `renewable_nz.transmission_lines` | `transmission_style` |
| `renewable_nz:roads` | `renewable_nz.roads` | `roads_style` |
| `renewable_nz:protected_areas` | `renewable_nz.protected_areas` | `protected_areas_style` |
| `renewable_nz:gir_locations` | `renewable_nz.gir_locations` | `gir_locations_style` |
| `renewable_nz:weather_resource_summary` | `renewable_nz.weather_resource_summary` | `weather_resource_style` |
| `renewable_nz:site_selection_candidates` | `renewable_nz.site_selection_candidates` | `site_selection_style` |

## Coordinate Reference Systems

Native CRS for PostGIS layers:

```text
EPSG:2193
```

Declared CRS:

```text
EPSG:2193
```

GeoServer can reproject WMS output to EPSG:3857 for Leaflet.

## WMS Endpoint

The frontend expects:

```text
http://localhost:8080/geoserver/renewable_nz/wms
```

If your GeoServer runs on another host or port, update `CONFIG.geoserverWmsUrl` in `frontend/app.js`.

## Publish Checklist

1. Run `database/schema.sql`, `database/sample_data.sql`, and `database/indexes.sql`.
2. Run the data pipelines that populate `gir_locations`, `weather_resource_summary`, and `site_selection_candidates`.
3. Confirm all geometry columns are EPSG:2193 using `database/spatial_queries.sql`.
4. Upload all SLD files in `geoserver/styles/`.
5. Publish each table as a GeoServer layer.
6. Assign the matching default style.
7. Open Layer Preview and test WMS output as PNG.
8. Enable `GeoServer WMS` in the frontend.
