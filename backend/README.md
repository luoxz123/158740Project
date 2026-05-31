# Backend Notes

The primary backend for this project is PostgreSQL/PostGIS plus GeoServer. This folder contains an optional FastAPI bridge for health checks and lightweight summary endpoints when the frontend needs JSON statistics in addition to WMS.

## Run

```powershell
pip install -r ../requirements.txt
copy .env.example .env
uvicorn app:app --reload --host 127.0.0.1 --port 9000
```

## Endpoints

- `GET /api/health`
- `GET /api/summary`
- `GET /api/gir-locations`

The frontend does not require this API for the default demo because it reads local GeoJSON files and can consume GeoServer WMS directly.
