# GIS Requirements

## Spatial Analysis

The project shall create renewable suitability layers using GIS analysis.

Recommended criteria:

- Wind speed or solar irradiance.
- Distance to transmission lines.
- Terrain slope.
- Road access.
- Protected area exclusion or penalty.

## CRS

All database geometry must use:

```text
EPSG:2193
```

Frontend GeoJSON may use EPSG:4326 for Leaflet display.

## Outputs

- Wind suitability polygons.
- Solar suitability polygons.
- Transmission line layer.
- Road access layer.
- Protected area layer.
- GIR extracted point layer.
- Historical weather resource point layer.
- Recommended site candidate point layer.
