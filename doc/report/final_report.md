# NZ Renewable Energy Suitability Explorer

**Postgraduate WebGIS Group Project Report**

**Project:** NZ Renewable Energy Suitability Explorer  
**Repository:** `https://github.com/luoxz123/158740`  
**Application URL on VM:** `http://localhost:8000` or `http://<VM-IP>:8000`  
**GeoServer URL:** `http://localhost:8080/geoserver` unless the VM port has been changed  
**GeoServer login:** `admin / geoserver` unless changed during installation  
**Database:** PostgreSQL/PostGIS database `renewable_nz`, schema `renewable_nz`  
**Database login used for deployment:** `postgres / Postgres123` unless overridden  

## Executive Summary

The NZ Renewable Energy Suitability Explorer is an open-source WebGIS application for screening potential wind farm and solar farm locations in New Zealand. The product integrates physical resource evidence, grid proximity, environmental constraints, road/context data, public text evidence, and an interactive mapping interface. The application was designed as a planning-level decision-support tool, not as a replacement for detailed engineering, environmental, land ownership, or consenting studies.

The main design challenge was to combine several different forms of evidence in a transparent and operational way. Wind and solar energy suitability are inherently spatial problems: suitable sites depend on resource quality, proximity to transmission infrastructure, accessibility, environmental constraints, and local geographic context. GIS-based multi-criteria decision analysis (GIS-MCDA) is widely used for this type of site-selection problem because it allows multiple spatial criteria to be standardised, weighted, and mapped (Malczewski, 2006; Latinopoulos and Kechagia, 2015). This project applies that principle using a simplified, defensible student-project model.

The implemented product includes a Leaflet web map, local GeoJSON fallback layers, a GeoServer WMS switch, PostGIS storage, Python data-processing pipelines, a Geographic Information Retrieval (GIR) pipeline, historical weather-resource processing, and a ranked candidate-site layer. The final site-selection model uses the existing 87-point weather resource dataset, inverse distance weighting (IDW) interpolation, distance to Transpower transmission lines, nearby GIR evidence, and interpolation confidence. The final score is:

```text
55% weather resource score
25% transmission proximity score
15% GIR evidence score
5% interpolation confidence
```

The application is deployable on the Windows VM using `deploy_windows_vm.bat`, and the frontend can be restarted using `start_frontend_windows.bat`.

## 1. Project Background and Problem Scope

New Zealand's electricity transition requires practical tools for identifying where renewable energy infrastructure may be suitable. Wind farms and solar farms need strong resource conditions, a realistic grid connection pathway, access for construction and maintenance, and avoidance or careful management of environmental constraints. A WebGIS is appropriate because these criteria are spatial and are more easily explored through an interactive map than through a static table.

The product was scoped around two technology types:

- Wind farms.
- Solar farms.

The project deliberately focuses on planning-level screening. It does not attempt to calculate final generation yield, grid capacity, land acquisition feasibility, consenting risk, turbine layout, wake loss, or detailed photovoltaic system design. Instead, it helps users identify promising areas that deserve further investigation.

The primary users are assumed to be:

- Planning students and lecturers assessing renewable-energy siting logic.
- Local or regional planning analysts who need an overview of suitable areas.
- Energy-sector stakeholders who want an early spatial screening tool.
- Non-specialist users who need a map-based explanation of why some locations score better than others.

The project objectives were:

1. Build an operational WebGIS site using open-source technologies.
2. Store and serve spatial data through PostGIS and GeoServer.
3. Provide interactive map functions such as layer toggling, legend, search, filtering, popups, heatmap visualisation, and WMS integration.
4. Implement a GIR workflow that extracts locations from renewable-energy-related web text.
5. Integrate weather resource data with grid and text evidence to recommend candidate wind and solar locations.
6. Provide a deployable project structure suitable for a Windows VM.

## 2. Design Process

### 2.1 Requirement Interpretation

The first design step was to translate the assignment requirements into concrete product requirements. The assignment required an operational website, spatial database, GIS web server, relevant datasets, interactive functions, and a written report. The AGENTS.md project specification further required Leaflet, PostgreSQL/PostGIS, GeoServer, Python, GeoJSON/CSV, GIR, and a professional government-planning style.

The functional requirements were interpreted as:

- Display wind and solar suitability layers.
- Display supporting context layers such as transmission lines, roads, and protected areas.
- Display GIR-derived point evidence.
- Display weather resource points.
- Provide recommended site candidates.
- Allow layer toggling and legend interpretation.
- Allow search and filtering.
- Provide popups with useful attribute information.
- Provide a heatmap.
- Provide optional GeoServer WMS display.

The non-functional requirements were interpreted as:

- Use open-source software only.
- Keep the system deployable on a constrained Windows VM.
- Keep the architecture understandable for a 4-week student project.
- Keep the data-processing steps repeatable through scripts.
- Store database geometry in EPSG:2193, the New Zealand Transverse Mercator projection.

This interpretation shaped the rest of the design. The product was built as a pragmatic WebGIS rather than a complex enterprise system.

### 2.2 Literature and Comparable Product Review

The literature review confirmed that renewable-energy siting is commonly addressed through GIS-MCDA. Malczewski (2006) reviews GIS-based multicriteria decision analysis and shows why GIS is useful for combining spatial criteria in decision problems. Latinopoulos and Kechagia (2015) apply GIS and multi-criteria evaluation to wind-farm site selection, using constraints and evaluation factors to produce suitability indices. Solar site-selection literature similarly emphasises solar radiation, slope, grid proximity, road access, and environmental exclusions as important factors (Aly et al., 2019; Solar PV Power Plants Site Selection review, 2018).

Comparable web tools also influenced the design. The Global Wind Atlas and Global Solar Atlas show that renewable-resource information is most useful when users can inspect it spatially through interactive maps and downloadable GIS data. Transpower's Maps and GIS Data page demonstrates the importance of transmission-network data in energy planning and provides official open access to infrastructure layers. These examples justified the project's emphasis on resource layers, grid proximity, popups, and map-based exploration.

The GIR literature also informed the text-processing workflow. Jones and Purves (2008) describe geographical information retrieval as a field concerned with geographically focused information needs and place references in text. GIR and geoparsing work commonly involves place-name extraction, toponym resolution, and geocoding. For this project, spaCy named-entity recognition and a New Zealand place-name fallback list were used to extract place names, while GeoPy/offline known-place coordinates were used to geocode them.

### 2.3 Data Model Design

The second design step was to identify the spatial layers needed for a credible renewable-energy suitability explorer. The selected layers were:

| Dataset | Role in the Product | Implementation |
|---|---|---|
| Wind suitability polygons | Planning-level wind suitability zones | `renewable_nz.wind_suitability`, `frontend/data/wind_suitability.geojson` |
| Solar suitability polygons | Planning-level solar suitability zones | `renewable_nz.solar_suitability`, `frontend/data/solar_suitability.geojson` |
| Transmission lines | Grid proximity and infrastructure context | `renewable_nz.transmission_lines`, Transpower Open Data |
| Roads | Access/context layer | `renewable_nz.roads` |
| Protected areas | Environmental constraint layer | `renewable_nz.protected_areas` |
| GIR locations | Text-derived renewable-energy place evidence | `renewable_nz.gir_locations` |
| Weather resource points | Wind and solar resource evidence | `renewable_nz.weather_resource_summary` |
| Site selection candidates | Final top 10 wind and top 10 solar recommendations | `renewable_nz.site_selection_candidates` |

All database geometry is stored in EPSG:2193. This was chosen because LINZ identifies NZTM2000 as the official projection used for New Zealand topographic mapping, and it supports metric distance operations better than unprojected latitude/longitude. Web display data is exported to EPSG:4326 GeoJSON for Leaflet and can be reprojected by GeoServer for WMS display.

The database schema is defined in:

```text
database/schema.sql
```

Indexes are defined in:

```text
database/indexes.sql
```

The schema uses PostGIS geometry types such as `MULTIPOLYGON`, `MULTILINESTRING`, and `POINT`, with validity checks to prevent broken geometry from entering the core tables. This supports reliable WMS rendering, spatial distance calculations, and frontend export.

### 2.4 Data Collection and Processing Design

The project uses three main data workflows.

The first workflow is the GIR pipeline:

```text
scripts/gir_pipeline.py
```

This pipeline collects or reads renewable-energy-related text, identifies relevant keywords, extracts New Zealand place names, geocodes the places, writes GeoJSON, and can insert records into PostGIS. Automatic discovery is supported for public news sites such as RNZ, Stuff, and NZ Herald. Facebook is handled through CSV/API export rather than blind scraping, because Facebook pages are commonly gated and subject to platform permissions.

The second workflow is the historical weather resource pipeline:

```text
scripts/weather_history_pipeline.py
```

This pipeline uses the Open-Meteo Historical Weather API to collect variables such as wind speed, wind gusts, shortwave radiation, and sunshine duration. Open-Meteo documentation lists these variables and provides historical hourly weather data for specified coordinates. The current project uses an 87-location New Zealand sample of rural, coastal, and inland analysis points. This design was chosen after investigating NIWA/Earth Sciences New Zealand VCSN data and finding that the cost was not suitable for a student project.

The third workflow is site selection:

```text
scripts/site_selection_analysis.py
```

This script combines weather resources, transmission-line distance, GIR evidence, and interpolation confidence. Candidate locations include original weather points and midpoint corridors between nearby points. Weather values at candidate points are estimated with IDW interpolation. IDW is a simple deterministic interpolation method where nearby points influence the estimate more strongly than distant points; it is appropriate here because the goal is planning-level screening from a limited point dataset, not high-resolution engineering-grade modelling.

Transmission line data is prepared by:

```text
scripts/import_transpower_lines.py
```

This script uses Transpower's public `TransmissionLines` ArcGIS FeatureServer, filters commissioned assets, simplifies geometry for browser and analysis performance, cleans invalid line geometry, writes frontend GeoJSON, and can insert the lines into PostGIS. This replaced the earlier small sample transmission layer and improved the candidate scoring around Tauranga, Napier, Hastings, and other areas.

#### 2.4.4 GIS Spatial Analysis

The project includes explicit GIS spatial analysis rather than only displaying downloaded layers. The purpose of this analysis is to turn raw spatial evidence into planning criteria for renewable-energy suitability. The main analysis operations are terrain screening, proximity analysis, accessibility analysis, and spatial exclusion.

**Slope analysis.** Slope is an important criterion for renewable-energy site selection, especially for solar farms. Solar panels are easier and cheaper to install on relatively flat or gently sloping land, while steep slopes can increase construction cost, access difficulty, erosion risk, and maintenance complexity. In the GIS design, slope values are generated from a DEM using standard terrain-processing tools in QGIS or raster GIS workflows. The resulting slope values are represented in the suitability tables using the `slope_degree` attribute in `wind_suitability` and `solar_suitability`. This allows the frontend popup and export workflow to show terrain suitability as part of the suitability evidence.

**Aspect analysis.** Aspect analysis was considered with the slope workflow because the direction of slope affects solar exposure. For the southern hemisphere, north-facing slopes generally receive better solar exposure than south-facing slopes. Therefore, south-facing slopes are treated as less suitable or excluded for solar-farm screening. This criterion is particularly relevant for solar farms because topographic orientation can affect the amount of usable radiation received by photovoltaic panels. In a full engineering model this would be combined with detailed solar radiation modelling; in this student WebGIS it is documented as a GIS screening criterion and reflected through the simplified solar suitability layer.

**Distance to transmission lines.** Grid proximity is one of the strongest practical feasibility factors because long grid connections increase cost and consenting complexity. The project therefore imports Transpower transmission lines and calculates the distance from suitability zones or candidate points to the nearest transmission geometry. This is implemented in PostGIS and in the candidate-site workflow. An example PostGIS proximity query is:

```sql
SELECT
    s.energy_type,
    s.region_name,
    ROUND((MIN(ST_Distance(s.geom, t.geom)) / 1000.0)::numeric, 2) AS nearest_grid_km
FROM suitability_all s
JOIN transmission_lines t
    ON ST_DWithin(s.geom, t.geom, 10000)
GROUP BY s.energy_type, s.region_name;
```

This query uses `ST_DWithin(...)` to limit the search to features within 10 km and `ST_Distance(...)` to calculate nearest transmission distance. The same logic supports the `distance_to_transmission_km` attribute in the ranked candidate-site layer.

**Distance to roads.** Road access is also included as a planning criterion because renewable-energy sites need access for construction vehicles, maintenance, and emergency response. The project includes a road corridor layer and publishes it in both PostGIS and the Leaflet frontend. Although road distance is not weighted as heavily as resource quality or transmission proximity in the final candidate score, the road layer supports visual accessibility analysis, popup inspection, search by road class, and future spatial queries such as nearest-road distance or buffer-based access screening.

Together, these spatial analyses demonstrate that the WebGIS is not only a visualisation product. It applies GIS operations to evaluate where renewable infrastructure is more realistic: suitable terrain, favourable solar orientation, close transmission access, road accessibility, and avoidance of protected areas.

### 2.5 Suitability and Candidate-Scoring Design

The scoring model was designed to be transparent. Each candidate site receives four component scores:

| Component | Weight | Reason |
|---|---:|---|
| Weather resource | 55% | Wind and solar farms primarily depend on resource quality. |
| Transmission proximity | 25% | Grid connection affects feasibility and cost. |
| GIR evidence | 15% | News/weather/public text provides contextual evidence of relevant places. |
| Interpolation confidence | 5% | Candidates closer to measured weather points are more reliable. |

The weighting gives the greatest influence to physical resource quality, which is consistent with wind and solar siting literature. Transmission proximity is the second largest factor because both solar and wind studies commonly include distance to power lines or substations as a feasibility criterion. GIR evidence receives a smaller but meaningful weight because it should support, not dominate, the physical model. Interpolation confidence is included to avoid over-ranking candidates that are far from measured weather locations.

The model is intentionally simple. More advanced work could include AHP pairwise comparison, sensitivity analysis, grid capacity, land ownership, slope rasters, land-use exclusions, and ecological constraints. For this project, the transparent weighted model was preferred because it is explainable during a 15-minute demonstration and realistic for a 4-week student project.

### 2.6 User Interface Design

The frontend was designed as a professional planning platform rather than a landing page. The first screen is the working map interface. A persistent left control panel contains search, filters, layer toggles, metrics, charts, and filtered results. The map occupies the main screen area.

This design was selected because GIS users need continuous access to both map layers and controls. Hiding controls behind separate pages would slow the workflow. A side-panel layout also resembles many public-sector planning and asset-viewer interfaces.

The interface includes:

- A Leaflet map centred on New Zealand.
- OpenStreetMap basemap tiles.
- Layer toggles for all project layers.
- A legend.
- Search by region, place, project name, road class, energy type, and article text.
- Energy type filter.
- Minimum suitability score slider.
- Popups for all important layers.
- Dashboard charts using Chart.js.
- Suitability heatmap.
- GeoServer WMS switch.
- Visible GeoJSON export.

The visual style uses restrained colours, moderate contrast, and a compact control panel. Wind suitability is styled in blue tones, solar in gold/yellow tones, transmission lines in dark line symbology, protected areas in green constraint styling, and recommended sites as prominent points.

### 2.7 Technology Design

The technology stack was chosen to meet the assignment requirement for open-source software and to reflect a standard WebGIS architecture.

| Technology | Role | Justification |
|---|---|---|
| Leaflet | Browser map client | Lightweight, open-source, supports GeoJSON, WMS, popups, and interactive controls. |
| Chart.js | Dashboard charts | Open-source HTML5 charting library suitable for simple dashboard summaries. |
| PostgreSQL/PostGIS | Spatial database | Robust open-source spatial database for geometry storage, indexing, spatial queries, and CRS transformations. |
| GeoServer | GIS web server | Open-source server supporting OGC WMS and SLD styling. |
| Python | Data processing | Suitable for repeatable workflows, API access, text processing, geocoding, and CSV/GeoJSON handling. |
| GeoJSON/CSV/SQL | Data exchange | Simple, open, and easy to inspect in a student project. |

PostGIS was selected because it spatially enables PostgreSQL and is widely used as a backend database for GIS and web-mapping applications. GeoServer was selected because it provides WMS support, SLD styling, and integration with PostGIS. Leaflet was selected because it is lightweight and supports the mapping functions required by the assignment without the overhead of a large frontend framework.

Docker deployment was attempted but rejected as the primary VM approach because the Windows VM did not have enough memory. The final deployment method therefore uses traditional Windows services and batch scripts. This is more stable for the available infrastructure.

#### 2.7.1 Alternative Technologies Considered

Several alternative technologies and data sources were considered before the final design was selected. Documenting these alternatives is important because the project was constrained by time, VM resources, data access, and the requirement to use open-source software.

| Alternative | Considered | Reason rejected or not selected |
|---|---|---|
| OpenLayers | Yes | OpenLayers is powerful and suitable for complex web mapping, but it has a steeper learning curve and more configuration overhead than Leaflet. Leaflet was sufficient for GeoJSON, WMS, popups, layer toggles, and the assignment timeframe. |
| MapServer | Yes | MapServer is a mature open-source web map server, but GeoServer provides a more accessible web administration interface, easier PostGIS publishing, and clearer SLD style management for a student deployment. |
| Docker deployment | Yes | Docker would make deployment more reproducible, but the Windows VM had limited memory. Running PostgreSQL, GeoServer, and the frontend through Docker was less stable than using the already installed VM services and batch scripts. |
| NIWA / Earth Sciences NZ VCSN API | Yes | VCSN would provide stronger gridded wind and solar evidence, but paid data access was not realistic for this student project. The project therefore used open Open-Meteo weather history and an 87-location sampling strategy. |
| Live MetService scraping | Yes | MetService contains useful warnings and weather information, but many pages are dynamic and not easy to collect reliably through simple static scraping. The project separated physical weather-resource collection from GIR text collection to keep the workflow stable. |
| Full backend REST API | Yes | A custom API would support dynamic database queries, but it would add development and deployment complexity. The project instead uses PostGIS/GeoServer for GIS services and local GeoJSON as a reliable fallback. |
| Raster-heavy suitability model | Yes | A full raster model using DEM, land cover, slope, aspect, solar radiation, and wind grids would be more sophisticated, but it would require larger datasets, more processing time, and more VM storage. The current vector/point model is more realistic for the four-week project. |
| QGIS-only desktop workflow | Yes | QGIS is useful for preparation and checking, but a desktop-only workflow would not satisfy the WebGIS requirement. The final design keeps QGIS as a processing support tool while delivering the product through a browser. |

The final stack was selected because it balances capability and practicality. Leaflet, PostGIS, GeoServer, Python, GeoJSON, and CSV are open-source, well documented, and realistic to deploy on the available VM. The rejected alternatives would be valid in a larger professional project, but they introduced unnecessary complexity, cost, or infrastructure risk for this assignment.

### 2.8 Deployment Design

The final deployment design assumes PostgreSQL/PostGIS and GeoServer are installed on the Windows VM. The project is cloned or downloaded from GitHub and deployed using:

```text
deploy_windows_vm.bat
```

This batch file:

1. Finds Python and `psql.exe`.
2. Installs Python dependencies.
3. Checks the PostGIS connection.
4. Rebuilds the `renewable_nz` schema.
5. Loads sample wind/solar/context layers.
6. Imports Transpower transmission lines.
7. Imports processed weather and GIR outputs.
8. Recomputes site candidates.
9. Validates GeoJSON.
10. Starts the frontend HTTP server.
11. Attempts GeoServer configuration if GeoServer is running.

The frontend alone can be restarted with:

```text
start_frontend_windows.bat
```

GeoServer can be configured or reconfigured with:

```text
configure_geoserver_windows.bat
```

This deployment approach avoids Docker memory overhead and is easier to troubleshoot on a teaching VM.

## 3. Product Architecture

### 3.1 Logical Architecture

The product follows a three-layer WebGIS architecture:

```text
Data processing layer
  Python scripts
  GIR collection
  Weather API processing
  Transpower line import
  Site selection analysis

Spatial data and service layer
  PostgreSQL/PostGIS
  GeoServer WMS
  SLD styles

Client layer
  Leaflet frontend
  Local GeoJSON fallback
  WMS mode
  Charts, popups, filters, search
```

The frontend can run in two modes:

1. Local GeoJSON mode, which reads files from `frontend/data/`.
2. GeoServer WMS mode, which requests layers from `renewable_nz` workspace WMS.

This dual-mode design improves reliability. If GeoServer is not running, the map still works with local GeoJSON. If GeoServer is running, the project demonstrates the full WebGIS service architecture required by the assignment.

### 3.2 Directory Structure

Important directories and files are:

| Path | Purpose |
|---|---|
| `frontend/index.html` | Main web application page. |
| `frontend/styles.css` | Interface layout and visual styling. |
| `frontend/app.js` | Leaflet map logic, layers, filters, popups, charts, export, and WMS switch. |
| `frontend/config.js` | GeoServer WMS URL configuration. |
| `frontend/data/` | GeoJSON layers used by local frontend mode. |
| `database/schema.sql` | PostGIS schema and views. |
| `database/sample_data.sql` | Sample wind/solar/context records. |
| `database/indexes.sql` | Spatial and attribute indexes. |
| `database/spatial_queries.sql` | Demonstration spatial queries. |
| `geoserver/workspace_config.md` | Manual GeoServer publishing instructions. |
| `geoserver/styles/` | SLD style files for GeoServer layers. |
| `scripts/gir_pipeline.py` | Web text GIR workflow. |
| `scripts/weather_history_pipeline.py` | Historical weather data workflow. |
| `scripts/import_transpower_lines.py` | Transpower transmission-line import workflow. |
| `scripts/site_selection_analysis.py` | Candidate site-ranking model. |
| `scripts/validate_geojson.py` | GeoJSON validation utility. |
| `deploy_windows_vm.bat` | Full traditional Windows VM deployment. |
| `start_frontend_windows.bat` | Starts only the frontend HTTP server. |
| `configure_geoserver_windows.bat` | Configures GeoServer workspace, store, styles, and layers. |
| `doc/report/` | Report and methodology documentation. |
| `doc/presentation/` | Demonstration flow and presentation script. |

### 3.3 Database Structure

The main PostGIS schema is:

```text
renewable_nz
```

Important tables:

| Table | Geometry | Description |
|---|---|---|
| `wind_suitability` | `MULTIPOLYGON, 2193` | Wind suitability zones. |
| `solar_suitability` | `MULTIPOLYGON, 2193` | Solar suitability zones. |
| `transmission_lines` | `MULTILINESTRING, 2193` | Transpower transmission line network. |
| `roads` | `MULTILINESTRING, 2193` | Road access/context corridors. |
| `protected_areas` | `MULTIPOLYGON, 2193` | Environmental constraint layer. |
| `gir_locations` | `POINT, 2193` | GIR-derived place mentions. |
| `weather_resource_summary` | `POINT, 2193` | Weather resource summaries. |
| `site_selection_candidates` | `POINT, 2193` | Ranked wind and solar candidate sites. |

Important views:

| View | Purpose |
|---|---|
| `suitability_all` | Combines wind and solar suitability polygons. |
| `suitability_web_mercator` | Provides suitability polygons transformed to EPSG:3857 for web display compatibility. |

### 3.4 GeoServer Structure

GeoServer workspace:

```text
renewable_nz
```

PostGIS store:

```text
postgis_renewable_nz
```

Expected WMS endpoint:

```text
http://localhost:8080/geoserver/renewable_nz/wms
```

Published WMS layers:

| GeoServer layer | PostGIS source | Style |
|---|---|---|
| `renewable_nz:wind_suitability` | `renewable_nz.wind_suitability` | `wind_style` |
| `renewable_nz:solar_suitability` | `renewable_nz.solar_suitability` | `solar_style` |
| `renewable_nz:transmission_lines` | `renewable_nz.transmission_lines` | `transmission_style` |
| `renewable_nz:roads` | `renewable_nz.roads` | `roads_style` |
| `renewable_nz:protected_areas` | `renewable_nz.protected_areas` | `protected_areas_style` |
| `renewable_nz:gir_locations` | `renewable_nz.gir_locations` | `gir_locations_style` |
| `renewable_nz:weather_resource_summary` | `renewable_nz.weather_resource_summary` | `weather_resource_style` |
| `renewable_nz:site_selection_candidates` | `renewable_nz.site_selection_candidates` | `site_selection_style` |

### 3.5 Access Instructions

On the VM, the application can be started from the project root:

```bat
start_frontend_windows.bat
```

Then open:

```text
http://localhost:8000
```

From another machine on the same network:

```text
http://<VM-IP>:8000
```

GeoServer:

```text
http://localhost:8080/geoserver
```

Default GeoServer credentials:

```text
admin / geoserver
```

PostGIS connection:

```text
Database: renewable_nz
Schema: renewable_nz
User: postgres
Password: Postgres123
```

If the GeoServer port is changed, update:

```text
frontend/config.js
```

and run:

```bat
set GEOSERVER_URL=http://localhost:<new-port>/geoserver
configure_geoserver_windows.bat
```

## 4. Site Functionality

### 4.1 Map Display

The main screen shows New Zealand with an OpenStreetMap basemap. The map starts at a national view and supports zooming and panning. Layers are drawn in separate panes so that polygons, lines, and points remain visually ordered.

### 4.2 Layer Control and Legend

The layer control panel allows users to turn individual layers on and off:

- Wind suitability.
- Solar suitability.
- Transmission lines.
- Road access corridors.
- Protected areas.
- GIR renewable mentions.
- Weather resource points.
- Recommended sites.
- Suitability heatmap.
- GeoServer WMS mode.

The legend explains the symbology. This is important because users need to distinguish suitability areas, constraints, infrastructure, text-derived points, and recommended sites.

### 4.3 Search

The search bar supports text search across feature properties. Users can search for:

- Region names.
- Place names.
- Candidate site names.
- Energy types.
- Road names/classes.
- GIR article titles.

Search results are returned in the side panel. Selecting or searching a result pans the map to the matching feature.

### 4.4 Suitability Filtering

The suitability controls include:

- Energy type filter: all, wind, or solar.
- Minimum score slider.

These controls update the map and results list. Lower-scoring areas remain visually subdued, while higher-scoring areas remain prominent. This helps users focus on more promising zones without completely losing geographic context.

### 4.5 Popups

Feature popups provide relevant information for each layer:

- Suitability zones show energy type, score, grid distance, and constraint level.
- Transmission lines show line name, voltage, operator, and source.
- Roads show road class and source.
- GIR points show article title, place name, energy type, source URL, and confidence.
- Weather resource points show wind speed, P90 wind speed, solar radiation, sunshine hours, and resource scores.
- Recommended sites show rank, final score, resource score, grid distance, GIR evidence, and related metrics.

Popup charts are generated with Chart.js for score-based features. This makes the interface more explanatory than a plain attribute table.

### 4.6 Dashboard

The dashboard summarises the number of visible suitable zones and top scores. It provides quick feedback when filters change. This is useful during demonstration and supports comparison between wind and solar results.

### 4.7 Heatmap

The heatmap layer provides a general visual impression of suitability intensity. It is generated from wind and solar suitability features. It is not a separate database table; it is a frontend visualisation derived from suitability data.

### 4.8 GeoServer WMS Mode

The WMS switch allows users to change from local GeoJSON layers to GeoServer WMS layers. This demonstrates the required GIS web server architecture. The local GeoJSON fallback remains useful for reliability, while WMS mode shows that the same project layers can be served from PostGIS through GeoServer.

### 4.9 Export Visible GeoJSON

The export button allows users to export currently visible local vector features as GeoJSON. This supports reuse in QGIS or another GIS environment and demonstrates practical data interoperability.

### 4.10 Recommended Sites

The recommended site layer is the main analytical output. It displays the top 10 wind and top 10 solar candidate sites. Each point contains:

- Rank.
- Energy type.
- Candidate name.
- Final score.
- Weather resource score.
- Transmission proximity score.
- GIR evidence score.
- Interpolation confidence.
- Distance to transmission lines.
- Weather resource variables.

The current Transpower update improved grid proximity in areas such as Tauranga, Napier, and Hastings. Gisborne remains farther from the Transpower transmission line layer in the current open data, which is a meaningful result rather than a bug.

## 5. Design Justification

### 5.1 Why GIS-MCDA Was Used

Renewable-energy site selection requires comparison of multiple spatial criteria. Wind speed or solar radiation alone is not enough: grid proximity, constraints, access, and planning context also matter. GIS-MCDA is widely used for such problems because it can represent each criterion spatially and combine them into a suitability score. Malczewski's review of GIS-MCDA provides the general methodological justification, while wind and solar siting studies show that this approach is common in renewable-energy planning.

### 5.2 Why Weather Resource Data Was Included

Wind and solar resources are the foundation of project feasibility. The project therefore includes wind speed at 100 m, P90 wind speed, shortwave solar radiation, and sunshine duration. Open-Meteo was used because it provides accessible historical weather variables for specified coordinates. The use of 87 rural/coastal/inland points is more appropriate than using only major cities because many wind and solar farms are located outside urban centres.

### 5.3 Why Transmission Lines Were Included

Transmission proximity affects connection feasibility and cost. Literature on solar PV site selection identifies proximity to power lines as an important suitability factor, while wind-farm site-selection literature commonly includes technical and economic factors such as access and grid connection. The project therefore includes Transpower transmission lines and uses distance to those lines as a scoring component.

### 5.4 Why Protected Areas Were Included

Renewable projects can conflict with conservation, ecological, and landscape values. A protected-area layer was included as an environmental constraint. The current implementation uses a simplified sample constraint layer for demonstration, but the structure supports replacing it with official protected-area datasets in future work.

### 5.5 Why GIR Was Included

Physical datasets do not capture all public and planning context. GIR adds a layer of text-derived geographic evidence from news and public documents. This supports the assignment requirement and demonstrates how unstructured information can be converted into map features. The pipeline follows common GIR steps: collect text, identify relevant documents, extract place names, geocode, and display results spatially.

### 5.6 Why Leaflet, PostGIS, and GeoServer Were Used

Leaflet was selected because it is lightweight, open source, and supports interactive web mapping functions such as popups, GeoJSON, tiled basemaps, and WMS layers. PostGIS was selected because it provides spatial types, indexing, and CRS transformation inside PostgreSQL. GeoServer was selected because it publishes PostGIS layers through OGC services such as WMS and supports SLD styling. This stack is a standard open-source WebGIS pattern.

### 5.7 Why Local GeoJSON Fallback Was Kept

The frontend can work without GeoServer by reading local GeoJSON. This was a deliberate stability decision. During development and marking, GeoServer configuration can fail because of service ports, firewall rules, or VM limitations. Local GeoJSON ensures the site remains demonstrable, while WMS mode still satisfies the GIS web server requirement when GeoServer is running.

### 5.8 Why Traditional Windows Deployment Was Used

Docker was initially prepared, but the Windows VM had insufficient memory for a stable Docker deployment. The final deployment uses installed PostgreSQL/PostGIS, installed GeoServer, Python, and batch scripts. This matches the VM constraints and is easier for the project team to debug.

## 6. Testing and Evaluation

Testing was performed at several levels.

Code checks:

- Python scripts were syntax-checked using `py_compile`.
- Frontend JavaScript was checked with Node syntax checks.
- GeoJSON files were validated with `scripts/validate_geojson.py`.

Database checks:

- Tables were created in `renewable_nz` schema.
- Geometry columns use EPSG:2193.
- Spatial indexes are defined.
- Geometry validity constraints are applied.
- Row counts are checked by `deploy_windows_vm.bat`.

Frontend checks:

- Layer toggles work in local GeoJSON mode.
- Popups display attributes.
- Search returns features by name and attributes.
- Score filters change the visible suitability results.
- Heatmap can be toggled.
- Recommended site features display ranked scores.

GeoServer checks:

- Workspace, datastore, styles, and layers can be configured through `configure_geoserver.py`.
- WMS endpoint is expected at `http://localhost:8080/geoserver/renewable_nz/wms`.
- The frontend WMS switch is configured for the published layer names.

The most important evaluation issue discovered during development was transmission-line bias. The earlier sample transmission layer did not represent lower North Island and eastern North Island infrastructure well enough. This caused Wellington and Hawke's Bay/Bay of Plenty distances to be unrealistic. The project was improved by importing Transpower's public transmission-line layer. This correction made the site-selection model more defensible.

## 7. Limitations

The product is a planning-level prototype. Main limitations are:

- Wind and solar resource data is based on Open-Meteo historical model/reanalysis variables rather than paid high-resolution NIWA VCSN data.
- The weather-resource layer uses 87 analysis points and IDW interpolation, not a continuous national raster.
- Protected areas and roads are simplified demonstration layers and should be replaced with official datasets for real planning use.
- Transmission proximity is represented by distance to lines, not available grid capacity, substation capacity, connection queue, or upgrade cost.
- Land ownership, parcel boundaries, zoning, slope rasters, cultural constraints, airports, settlements, and consenting constraints are not fully modelled.
- GIR evidence is dependent on public web text availability and place-name extraction quality.
- The suitability weights are transparent but not calibrated through stakeholder consultation or formal AHP.

These limitations are acceptable for the assignment scope because the product demonstrates the complete WebGIS workflow: data collection, processing, database integration, web service publishing, and interactive mapping.

## 8. Future Work

Future improvements should include:

- Replace sample protected areas with official DOC/LINZ conservation datasets.
- Replace road samples with official LINZ or OpenStreetMap road networks.
- Add high-resolution slope and land-cover rasters.
- Add substations and grid-capacity information.
- Add parcel ownership and district planning zones.
- Add sensitivity analysis for site-selection weights.
- Add a time slider for weather history or seasonal resource variation.
- Add WFS or API endpoints for feature-level querying from PostGIS.
- Improve GIR by adding stronger toponym disambiguation and source filtering.
- Produce a PDF export/report button for selected candidate sites.

## 9. Conclusion

The NZ Renewable Energy Suitability Explorer meets the main Assignment 3 requirements. It is an operational WebGIS product using open-source technologies, includes multiple datasets, implements GIR, stores data in PostGIS, supports GeoServer WMS, and provides interactive map functions. The design process followed a practical GIS-MCDA approach supported by literature on renewable-energy site selection. The product is deployable on a constrained Windows VM through batch scripts and can be accessed through a browser.

The main value of the project is the integration of multiple evidence types into one planning interface: weather resource data, transmission lines, protected areas, road context, GIR text evidence, and ranked site candidates. The result is not a final engineering model, but it is a useful screening tool and a complete demonstration of WebGIS design, data integration, and interactive spatial decision support.

## References

Aly, A., Jensen, S. S. and Pedersen, A. B. (2019). GIS-Based Solar Radiation Mapping, Site Evaluation, and Potential Assessment: A Review. *Applied Sciences*, 9(9), 1960. https://www.mdpi.com/2076-3417/9/9/1960

Chart.js (2026). Chart.js: Open source HTML5 charts for your website. https://www.chartjs.org/

GeoServer (2026). WMS basics: GeoServer provides support for OGC Web Map Service versions 1.1.1 and 1.3.0. https://docs.geoserver.org/latest/en/user/services/wms/basics/

Global Solar Atlas (2026). About Global Solar Atlas. https://globalsolaratlas.info/support/about

Global Wind Atlas / DTU Wind Energy (2026). Global Wind Atlas overview and downloadable wind resource data. https://wasp.dtu.dk/en/wind-atlases/global-wind-atlas

Jones, C. B. and Purves, R. S. (2008). Geographical information retrieval. *International Journal of Geographical Information Science*, 22(3), 219-228. https://doi.org/10.1080/13658810701626343

Latinopoulos, D. and Kechagia, K. (2015). A GIS-based multi-criteria evaluation for wind farm site selection: A regional scale application in Greece. *Renewable Energy*, 78, 550-560. https://doi.org/10.1016/j.renene.2015.01.041

Leaflet (2026). Leaflet: an open-source JavaScript library for mobile-friendly interactive maps. https://leafletjs.com/

LINZ (2026). New Zealand Transverse Mercator 2000 (NZTM2000). https://www.linz.govt.nz/guidance/geodetic-system/coordinate-systems-used-new-zealand/projections/new-zealand-transverse-mercator-2000-nztm2000

Malczewski, J. (2006). GIS-based multicriteria decision analysis: a survey of the literature. *International Journal of Geographical Information Science*, 20(7), 703-726. https://doi.org/10.1080/13658810600661508

Open-Meteo (2026). Historical Weather API documentation. https://open-meteo.com/en/docs/historical-weather-api

PostGIS Project (2026). PostGIS documentation and getting started guide. https://postgis.net/documentation/getting_started/

Shepard, D. (1968). A two-dimensional interpolation function for irregularly-spaced data. *Proceedings of the 1968 ACM National Conference*, 517-524. https://doi.org/10.1145/800186.810616

Solar PV Power Plants Site Selection: A Review (2018). Summary of solar PV site-selection criteria including solar irradiation, power lines, slope, protected lands and watercourses. https://www.sciencedirect.com/science/chapter/edited-volume/abs/pii/B9780128129593000022

Transpower (2026). Maps and GIS Data. https://www.transpower.co.nz/our-work/industry/our-grid/maps-and-gis-data
