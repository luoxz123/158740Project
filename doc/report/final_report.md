# NZ Renewable Energy Suitability Explorer

## 1. Project Goal

The NZ Renewable Energy Suitability Explorer is a WebGIS platform designed to help users identify promising locations for wind farm and solar farm development in New Zealand. The application combines physical resource evidence, network access, environmental constraints, public text evidence, and interactive visualisation. The goal is not to replace engineering or consenting studies, but to provide an operational planning-level screening tool.

## 2. Problem Scoping

Renewable energy siting is a spatial decision problem. Wind and solar projects need strong physical resources, access to transmission infrastructure, reasonable terrain and access conditions, and limited conflict with protected areas. Public discussion and news coverage can also reveal locations where renewable-energy projects, power supply, or weather conditions are already important.

The project therefore treats suitability as a multi-criteria WebGIS problem. Wind resource potential is represented by 100 m wind speed and high-percentile wind speed. Solar potential is represented by shortwave radiation and sunshine hours. Grid access is represented by distance to transmission lines. Environmental constraints are represented by protected area polygons. Geographic Information Retrieval (GIR) adds a text-derived evidence layer from renewable-energy-related web pages.

## 3. Data Collection And Integration

The system includes several spatial datasets:

- Wind suitability polygons.
- Solar suitability polygons.
- Transmission line corridors.
- Road access corridors.
- Protected areas.
- Weather resource points.
- GIR renewable-energy mention points.
- Recommended wind and solar site candidates.

The project uses two self-created data workflows. First, `scripts/gir_pipeline.py` performs web text collection, keyword filtering, place-name extraction, geocoding, GeoJSON export, and optional PostGIS insertion. This implements the GIR requirement from the course. Second, `scripts/site_selection_analysis.py` uses the 87-point weather resource dataset, inverse distance weighting, grid distance, and GIR evidence to rank candidate wind and solar sites.

The weather dataset is produced by `scripts/weather_history_pipeline.py`, which collects historical wind speed, gust, solar radiation, and sunshine duration for rural, coastal, and inland analysis points. NIWA VCSN was investigated, but its bulk data cost was not suitable for the student project budget. The project therefore uses the already collected open weather dataset and documents VCSN as a future improvement.

All core spatial data is represented in PostGIS using EPSG:2193. Web display layers are also exported as GeoJSON in EPSG:4326 for Leaflet.

## 4. Application Design

The interface is designed as a professional planning platform rather than a public marketing page. It uses a persistent left control panel and a full-height interactive map. This layout keeps the map central while leaving space for filters, dashboards, and results.

The application includes the required functions:

- A layer control panel and legend.
- Search by location and attribute text.
- Popups with information about selected features.

It also includes project-specific functions:

- Energy type and minimum score filters.
- Chart.js dashboard summaries.
- Suitability heatmap.
- GeoServer WMS switch.
- Visible layer GeoJSON export.
- Recommended site layer showing ranked wind and solar candidates.

The design follows common WebGIS usability principles: make map layers discoverable, keep controls visible, use consistent symbology, and allow users to query features directly through popups and search.

## 5. Technology Selection

All selected software is open source:

- Leaflet for browser map display.
- Chart.js for dashboard visualisation.
- PostgreSQL/PostGIS for spatial database storage.
- GeoServer for WMS publication.
- Python for GIR, weather data processing, and site selection.
- QGIS-compatible data formats such as GeoJSON, CSV, and PostGIS tables.

This stack is appropriate because PostGIS and GeoServer provide a standard open WebGIS architecture, while Leaflet provides a lightweight and reliable browser client. Python is suitable for repeatable data processing and text extraction.

## 6. Implementation

The database is defined in `database/schema.sql`, with indexes in `database/indexes.sql` and test queries in `database/spatial_queries.sql`. The database includes tables for suitability layers, context layers, GIR points, weather resources, and site selection candidates.

GeoServer configuration is documented in `geoserver/workspace_config.md`. SLD styles are included for wind, solar, transmission, roads, protected areas, GIR, weather resource points, and recommended site candidates.

The frontend is implemented in `frontend/index.html`, `frontend/styles.css`, and `frontend/app.js`. The frontend can use local GeoJSON files for reliability and can switch to GeoServer WMS once layers are published on the VM.

## 7. Site Selection Analysis

The site selection model ranks wind and solar candidates separately. Candidate points include the original weather analysis points and midpoint corridors between nearby points. Weather values are estimated using inverse distance weighting. Each candidate receives a final score:

```text
55% weather resource score
25% transmission proximity score
15% GIR evidence score
5% interpolation confidence
```

The current wind result correctly identifies Wellington wind locations after improving the sample transmission corridor:

- Makara.
- Makara - Ohariu Valley corridor.
- Ohariu Valley.

The current solar result favours Canterbury and Waikato/Auckland corridor locations where resource, grid proximity, and GIR evidence are strong.

## 8. Testing And Evaluation

The following checks have been performed during development:

- Python syntax checks for processing scripts.
- JavaScript syntax checks for the frontend.
- GeoJSON validation for generated layers.
- Manual review of candidate rankings and correction of an identified transmission-line bias.

Before submission, the following live VM tests should be completed:

- Publish every PostGIS table in GeoServer.
- Confirm each WMS layer loads in GeoServer Layer Preview.
- Open the frontend through the VM host name from a Massey-network machine.
- Test layer toggles, popups, search, filters, heatmap, dashboard, export, and WMS mode.

## 9. Limitations And Future Work

This project is a planning-level screening system. It does not include land ownership, consenting constraints, detailed engineering, turbine wake modelling, high-resolution terrain modelling, or detailed grid capacity analysis. Future work should add official transmission capacity data, parcel ownership, high-resolution topography, real protected-area datasets, and NIWA VCSN data if budget allows.

## 10. Key Files

- `frontend/index.html`: web application entry point.
- `frontend/app.js`: map logic, layers, filters, search, popups, dashboard.
- `database/schema.sql`: PostGIS schema.
- `geoserver/workspace_config.md`: GeoServer publish instructions.
- `scripts/gir_pipeline.py`: GIR text processing.
- `scripts/weather_history_pipeline.py`: historical weather data collection.
- `scripts/site_selection_analysis.py`: candidate site ranking.
- `doc/report/assignment_compliance_matrix.md`: assignment requirement checklist.
