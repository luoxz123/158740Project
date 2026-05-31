# GIR Requirements

## Objective

Implement a lightweight Geographic Information Retrieval (GIR) workflow for renewable-energy-related web content.

This requirement covers unstructured web text. Historical wind speed, sunshine duration, and solar radiation are collected through the separate weather resource pipeline.

---

# Workflow

## Step 1 - Web Scraping

Scrape renewable energy articles from:

- RNZ
- NZ Herald
- Stuff

Keywords:

- wind farm
- solar farm
- renewable energy

---

## Step 2 - Named Entity Recognition

Use spaCy NER to extract:

- GPE
- LOC
- FAC

from article text.

---

## Step 3 - Geocoding

Use GeoPy to convert extracted place names into:

- latitude
- longitude

---

## Step 4 - GeoJSON Export

Generate GeoJSON containing:

- article title
- place name
- coordinates
- energy type

---

## Step 5 - GIS Integration

Import generated GeoJSON into:

- PostGIS
- GeoServer
- Leaflet

---

# Required Python Libraries

- requests
- beautifulsoup4
- spacy
- geopy
- geopandas
- pandas

---

# Output Format

GeoJSON FeatureCollection
