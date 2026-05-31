# Presentation Script

## Opening

This project is the NZ Renewable Energy Suitability Explorer, a WebGIS platform for identifying candidate wind and solar infrastructure locations in New Zealand.

## Problem

Renewable energy planning depends on location. Suitable sites need good energy resources, grid access, workable terrain, and low conflict with protected areas.

## System

The system uses PostGIS for spatial storage, GeoServer for WMS publishing, and Leaflet for the browser interface. It also includes a GIR pipeline that extracts renewable-energy-related places from web articles and maps them as a point layer.

## Demonstration

The map shows wind and solar suitability zones, transmission lines, protected areas, and GIR extracted locations. Users can filter by energy type and suitability score, search for locations, open popups, and compare dashboard charts.

## Conclusion

The project demonstrates a realistic open-source WebGIS workflow that combines spatial analysis, GIR, database-backed map services, and interactive planning visualisation.
