# Backend Requirements

The main backend shall use open-source GIS services:

- PostgreSQL
- PostGIS
- GeoServer

## Optional API

The optional FastAPI bridge may provide:

- Health check endpoint.
- Suitability summary endpoint.
- GIR locations endpoint.

The frontend must still run without this API by using local GeoJSON and GeoServer WMS.
