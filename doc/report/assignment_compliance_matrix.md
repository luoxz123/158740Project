# Assignment 3 Compliance Matrix

This matrix checks the project against the Assignment 3 group project requirements.

## Project Scoping

| Requirement | Current Status | Evidence |
|---|---|---|
| Understand the project problem space | Met | Renewable energy infrastructure siting is scoped around wind and solar resource potential, grid access, environmental constraints, and public text evidence. |
| Investigate related mapping approaches | Mostly met | The report materials discuss WebGIS planning patterns and suitability workflows. This can be expanded with more explicit examples in the final written report. |
| Identify useful datasets | Met | Weather resource data, transmission lines, protected areas, roads, GIR mentions, and generated candidate sites are included. |

## Data Collection, Formatting, And Integration

| Requirement | Current Status | Evidence |
|---|---|---|
| Range of relevant datasets | Met | Wind suitability, solar suitability, transmission lines, roads, protected areas, weather resource points, GIR points, and recommended sites. |
| Base data for context | Met after update | `frontend/data/roads.geojson` and OSM basemap provide access and map context. |
| Significant data collection/integration | Met | `weather_history_pipeline.py`, `gir_pipeline.py`, and `site_selection_analysis.py` collect, process, and integrate data. |
| Existing data from other sources | Met | OpenStreetMap basemap, Transpower-style transmission context, protected area sample layer, and Open-Meteo weather resource data. |
| Created datasets using at least two methods | Met | GIS analysis/site selection scoring and GIR/web text extraction are both implemented. |
| Data imported into spatial database | Met | `schema.sql` contains PostGIS tables for suitability, context layers, GIR, weather resources, and site selection candidates. |

## Design

| Requirement | Current Status | Evidence |
|---|---|---|
| Layer switcher / legend | Met | Frontend layer panel and map legend. |
| Search by location | Met | Search covers region, place, candidate, article, and layer attributes. |
| Search/filter by other data aspect | Met | Energy type and minimum score filters; search also covers energy type, candidate name, road class, and attributes. |
| Additional information for selected object | Met | Popups for suitability, GIR, weather, roads, and recommended sites. |
| Additional project-specific functionality | Met | Suitability filters, dashboard charts, heatmap, WMS toggle, visible-layer GeoJSON export, and ranked candidate site selection. |
| Professional web map presentation | Met | Responsive Leaflet interface with restrained planning-platform styling. |

## Technology Selection

| Requirement | Current Status | Evidence |
|---|---|---|
| Open-source software only | Met | Leaflet, Chart.js, PostgreSQL/PostGIS, GeoServer, Python, QGIS-compatible workflow. |
| Appropriate technology choice | Met | PostGIS stores spatial data, GeoServer publishes WMS, Leaflet displays local GeoJSON/WMS, Python performs GIR and analysis. |

## Implementation

| Requirement | Current Status | Evidence |
|---|---|---|
| Geospatial database | Met | `database/schema.sql`, `sample_data.sql`, `indexes.sql`, spatial queries. |
| GIS web server | Met in configuration | `geoserver/workspace_config.md` and SLD files define publishable WMS layers. Actual VM GeoServer must still be checked live. |
| Web mapping application | Met | `frontend/index.html`, `styles.css`, `app.js`, local GeoJSON layers, and WMS switch. |
| Operational on VM | Partly external | Project files and setup are ready; final confirmation requires testing on the Massey VM after deployment. |

## Deliverables

| Requirement | Current Status | Evidence |
|---|---|---|
| Operational website | Project-ready | Frontend can run with `python -m http.server 8000`; VM deployment still needs final live check. |
| Report no longer than 30 pages | Draft provided | `doc/report/final_report.md` is a report draft/structure. |
| 15 minute presentation | Met | `doc/presentation/script.md` and `demo_flow.md`. |
| Individual reflective essay | Not included | This is individual work and should be written separately by each student. |

## Remaining Live Checks

- Publish all GeoServer layers and test WMS previews.
- Confirm PostGIS tables are populated on the VM.
- Open the frontend from another Massey-network machine.
- Record the live demonstration video using the deployed VM site.
