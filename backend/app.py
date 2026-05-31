"""Optional FastAPI bridge for PostGIS summary data."""

from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

app = FastAPI(title="NZ Renewable Energy Suitability API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def db_config() -> dict[str, str | int]:
    return {
        "host": os.getenv("POSTGIS_HOST", "localhost"),
        "port": int(os.getenv("POSTGIS_PORT", "5432")),
        "dbname": os.getenv("POSTGIS_DB", "renewable_nz"),
        "user": os.getenv("POSTGIS_USER", "postgres"),
        "password": os.getenv("POSTGIS_PASSWORD", "postgres"),
    }


@contextmanager
def connection():
    conn = psycopg2.connect(**db_config())
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(sql: str) -> list[dict]:
    try:
        with connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(sql)
                return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT PostGIS_Version();")
                version = cursor.fetchone()[0]
        return {"status": "ok", "postgis": version}
    except psycopg2.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/summary")
def summary() -> dict[str, list[dict]]:
    rows = fetch_all(
        """
        SELECT
            energy_type,
            COUNT(*) AS zone_count,
            ROUND(AVG(suitability_score), 1) AS avg_score,
            MAX(suitability_score) AS top_score
        FROM renewable_nz.suitability_all
        GROUP BY energy_type
        ORDER BY energy_type;
        """
    )
    return {"summary": rows}


@app.get("/api/gir-locations")
def gir_locations() -> dict[str, list[dict]]:
    rows = fetch_all(
        """
        SELECT
            id,
            article_title,
            place_name,
            latitude,
            longitude,
            energy_type,
            source_url,
            confidence
        FROM renewable_nz.gir_locations
        ORDER BY id;
        """
    )
    return {"features": rows}
