# Methodology

## Suitability Analysis

The suitability model uses a weighted GIS overlay approach. Candidate renewable energy zones are evaluated against factors that are realistic for wind and solar planning:

- Resource potential: wind speed or solar irradiance.
- Grid proximity: distance to transmission infrastructure.
- Terrain suitability: slope and developable land characteristics.
- Environmental constraints: protected areas and conservation buffers.
- Access: proximity to road corridors.

Each factor is normalised to a common 0 to 100 suitability scale. The final score is stored in PostGIS as `suitability_score`.

## GIR Workflow

The GIR workflow creates a project-specific data layer from renewable-energy-related web text:

1. Collect renewable energy articles from selected New Zealand news websites.
2. Extract named places using SpaCy NER labels `GPE`, `LOC`, and `FAC`.
3. Geocode extracted place names using GeoPy and Nominatim.
4. Export points as GeoJSON.
5. Load GIR points into PostGIS and display them in Leaflet.

The GIR layer helps connect public discussion and news coverage to the suitability analysis.

## Historical Weather Resource Workflow

The weather resource workflow creates a separate evidence layer for wind and solar potential:

1. Read analysis locations from `data/raw/weather_locations.csv`.
2. Download historical hourly wind speed, wind gust, sunshine duration, and shortwave radiation.
3. Summarise each location into annual or custom-period resource metrics.
4. Export CSV and GeoJSON outputs.
5. Load weather resource points into PostGIS and display them in Leaflet.

This layer is not GIR. It supports the physical resource side of the suitability model, while the GIR layer supports public text and place-name evidence.

## CRS Management

All database geometry is stored in EPSG:2193. Web display data is reprojected to EPSG:4326 or EPSG:3857 as required by Leaflet and GeoServer WMS.
