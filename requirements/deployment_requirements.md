# Deployment Requirements

## Local Development

Recommended local services:

- PostgreSQL/PostGIS on port 5432.
- GeoServer on port 8080.
- Frontend static server on port 8000.
- Optional FastAPI bridge on port 9000.

## Open Source Constraint

Only open-source software should be used.

## Demo Reliability

The frontend must work with local sample GeoJSON even if GeoServer is not running. GeoServer WMS should be available for integration testing and final demonstration.
