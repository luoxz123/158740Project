# AGENTS.md

## Project Overview

This project is a postgraduate-level WebGIS platform named:

NZ Renewable Energy Suitability Explorer

The system helps users identify optimal locations for renewable energy infrastructure in New Zealand, including:

- Wind farms
- Solar farms

The project combines:

- GIS spatial analysis
- Geographic Information Retrieval (GIR)
- WebGIS technologies
- Interactive map visualisation

---

# Technology Stack

## Frontend

- Leaflet
- HTML5
- CSS3
- JavaScript
- Chart.js

## Backend

- PostgreSQL
- PostGIS
- GeoServer

## GIS Processing

- QGIS
- Python

## Data Formats

- GeoJSON
- Shapefile
- Raster TIFF
- CSV

---

# Coding Standards

## General Rules

- Write clean and modular code
- Use reusable functions
- Use comments in English only
- Avoid unnecessary complexity
- Prefer readable code over clever code
- Keep UI modern and minimalistic

---

# GIS Requirements

The system must support:

- Layer toggling
- Spatial filtering
- Search functionality
- Popup information display
- Renewable suitability visualisation
- Heatmap visualisation
- GeoServer WMS integration

---

# GIR Requirements

The project must implement Geographic Information Retrieval (GIR) functionality.

## GIR Pipeline

1. Scrape renewable-energy-related web articles
2. Extract place names using SpaCy NER
3. Geocode place names using GeoPy
4. Generate GeoJSON layers
5. Display extracted locations on Leaflet map

---

# Frontend Requirements

The frontend must include:

- Responsive UI
- Layer control panel
- Search bar
- Popup windows
- Dashboard charts
- Legend panel
- Renewable suitability filters

---

# Database Requirements

The database must contain:

- Renewable suitability layers
- Wind datasets
- Solar datasets
- Transmission line layers
- Protected areas
- GIR extracted point layers

All geometry must use:

EPSG:2193 (NZTM2000)

---

# GeoServer Requirements

GeoServer must provide:

- WMS layers
- Styled SLD layers
- Raster support
- Vector support

---

# UI Design Requirements

The UI should resemble a professional government planning platform.

Preferred design characteristics:

- Clean layout
- Modern styling
- Dark/light contrast
- Professional GIS appearance

---

# Expected Deliverables

- Fully operational WebGIS platform
- GeoServer integration
- PostGIS integration
- GIS suitability analysis
- GIR text extraction pipeline
- Dashboard visualisation
- Final report
- Presentation materials

---

# Testing Requirements

Before completion:

- Test all WMS layers
- Test popup functionality
- Test search functionality
- Validate CRS consistency
- Validate GeoJSON outputs
- Check frontend responsiveness

---

# Important Constraints

- Use open-source software only
- Avoid proprietary GIS platforms
- Keep implementation realistic for a 4-week student project
- Prioritise stability over unnecessary complexity