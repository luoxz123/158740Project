"""Historical weather resource pipeline for renewable suitability analysis.

This script downloads historical wind and solar resource variables for selected
New Zealand locations using the Open-Meteo Historical Weather API.

Outputs:
- hourly CSV records
- per-location resource summary CSV
- per-location resource summary GeoJSON
- optional PostGIS table insertion
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import time
import urllib.parse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCATIONS = PROJECT_ROOT / "data" / "raw" / "weather_locations_extended.csv"
CITY_SAMPLE_LOCATIONS = PROJECT_ROOT / "data" / "raw" / "weather_locations.csv"
DEFAULT_HOURLY_CSV = PROJECT_ROOT / "data" / "processed" / "weather_hourly_history.csv"
DEFAULT_SUMMARY_CSV = PROJECT_ROOT / "data" / "processed" / "weather_resource_summary.csv"
DEFAULT_SUMMARY_GEOJSON = PROJECT_ROOT / "frontend" / "data" / "weather_resource_summary.geojson"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARIABLES = [
    "wind_speed_10m",
    "wind_speed_100m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "sunshine_duration",
]


@dataclass
class WeatherLocation:
    place_name: str
    latitude: float
    longitude: float
    region: str


def log(message: str) -> None:
    print(message, flush=True)


def require_requests() -> None:
    if requests is None:
        raise RuntimeError("This script requires requests. Install with: py -m pip install requests")


def read_locations(path: Path) -> list[WeatherLocation]:
    locations: list[WeatherLocation] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            locations.append(
                WeatherLocation(
                    place_name=row["place_name"].strip(),
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    region=(row.get("region") or "").strip(),
                )
            )
    return locations


def request_open_meteo(location: WeatherLocation, start_date: str, end_date: str, timeout: int) -> dict:
    require_requests()
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "Pacific/Auckland",
        "wind_speed_unit": "ms",
    }
    url = f"{OPEN_METEO_ARCHIVE_URL}?{urllib.parse.urlencode(params)}"
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rows_from_response(location: WeatherLocation, payload: dict) -> list[dict]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    rows: list[dict] = []

    for index, timestamp in enumerate(times):
        row = {
            "place_name": location.place_name,
            "region": location.region,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "time": timestamp,
        }
        for variable in HOURLY_VARIABLES:
            values = hourly.get(variable) or []
            row[variable] = safe_float(values[index]) if index < len(values) else None
        rows.append(row)
    return rows


def mean(values: list[float]) -> float | None:
    valid = [value for value in values if value is not None]
    if not valid:
        return None
    return statistics.fmean(valid)


def percentile(values: list[float], pct: float) -> float | None:
    valid = sorted(value for value in values if value is not None)
    if not valid:
        return None
    index = round((len(valid) - 1) * pct)
    return valid[index]


def summarise_location(location: WeatherLocation, rows: list[dict], start_date: str, end_date: str) -> dict:
    wind10 = [row["wind_speed_10m"] for row in rows]
    wind100 = [row["wind_speed_100m"] for row in rows]
    gust10 = [row["wind_gusts_10m"] for row in rows]
    radiation = [row["shortwave_radiation"] for row in rows]
    sunshine_seconds = [row["sunshine_duration"] for row in rows]

    total_shortwave_kwh_m2 = sum(value for value in radiation if value is not None) / 1000.0
    total_sunshine_hours = sum(value for value in sunshine_seconds if value is not None) / 3600.0
    mean_wind100 = mean(wind100)
    mean_radiation = mean(radiation)

    wind_score = min(100.0, max(0.0, ((mean_wind100 or 0.0) / 9.0) * 100.0))
    solar_score = min(100.0, max(0.0, (total_shortwave_kwh_m2 / max(1, len(rows) / 24) / 6.0) * 100.0))

    return {
        "place_name": location.place_name,
        "region": location.region,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hour_count": len(rows),
        "mean_wind_speed_10m_ms": round(mean(wind10) or 0.0, 3),
        "mean_wind_speed_100m_ms": round(mean_wind100 or 0.0, 3),
        "p90_wind_speed_100m_ms": round(percentile(wind100, 0.9) or 0.0, 3),
        "max_wind_gust_10m_ms": round(max([value for value in gust10 if value is not None], default=0.0), 3),
        "mean_shortwave_radiation_wm2": round(mean_radiation or 0.0, 3),
        "total_shortwave_radiation_kwh_m2": round(total_shortwave_kwh_m2, 3),
        "total_sunshine_hours": round(total_sunshine_hours, 2),
        "wind_resource_score": round(wind_score, 1),
        "solar_resource_score": round(solar_score, 1),
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_geojson(path: Path, summaries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for summary in summaries:
        properties = dict(summary)
        longitude = properties.pop("longitude")
        latitude = properties.pop("latitude")
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
            }
        )
    collection = {
        "type": "FeatureCollection",
        "name": "weather_resource_summary",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
    }
    path.write_text(json.dumps(collection, indent=2), encoding="utf-8")


def validate_sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid SQL identifier: {value}")
    return value


def default_db_dsn() -> str:
    if os.getenv("POSTGIS_DSN"):
        return os.environ["POSTGIS_DSN"]

    host = os.getenv("POSTGIS_HOST", "localhost")
    port = os.getenv("POSTGIS_PORT", "5432")
    dbname = os.getenv("POSTGIS_DB", "renewable_nz")
    user = os.getenv("POSTGIS_USER", "postgres")
    password = os.getenv("POSTGIS_PASSWORD", "")
    parts = [
        f"host={host}",
        f"port={port}",
        f"dbname={dbname}",
        f"user={user}",
    ]
    if password:
        parts.append(f"password={password}")
    return " ".join(parts)


def insert_summaries_to_postgis(summaries: list[dict], db_dsn: str, schema: str) -> int:
    if psycopg2 is None:
        raise RuntimeError("PostGIS insertion requires psycopg2-binary.")
    schema = validate_sql_identifier(schema)

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {schema}.weather_resource_summary (
            id SERIAL PRIMARY KEY,
            place_name VARCHAR(140) NOT NULL,
            region VARCHAR(140),
            latitude NUMERIC(9,6) NOT NULL,
            longitude NUMERIC(9,6) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            hour_count INTEGER NOT NULL,
            mean_wind_speed_10m_ms NUMERIC(8,3),
            mean_wind_speed_100m_ms NUMERIC(8,3),
            p90_wind_speed_100m_ms NUMERIC(8,3),
            max_wind_gust_10m_ms NUMERIC(8,3),
            mean_shortwave_radiation_wm2 NUMERIC(10,3),
            total_shortwave_radiation_kwh_m2 NUMERIC(12,3),
            total_sunshine_hours NUMERIC(12,2),
            wind_resource_score NUMERIC(5,1),
            solar_resource_score NUMERIC(5,1),
            data_source TEXT NOT NULL DEFAULT 'Open-Meteo Historical Weather API',
            geom geometry(POINT, 2193) NOT NULL,
            UNIQUE (place_name, start_date, end_date)
        );
        CREATE INDEX IF NOT EXISTS weather_resource_summary_geom_gix
            ON {schema}.weather_resource_summary USING GIST (geom);
    """

    insert_sql = f"""
        INSERT INTO {schema}.weather_resource_summary (
            place_name,
            region,
            latitude,
            longitude,
            start_date,
            end_date,
            hour_count,
            mean_wind_speed_10m_ms,
            mean_wind_speed_100m_ms,
            p90_wind_speed_100m_ms,
            max_wind_gust_10m_ms,
            mean_shortwave_radiation_wm2,
            total_shortwave_radiation_kwh_m2,
            total_sunshine_hours,
            wind_resource_score,
            solar_resource_score,
            geom
        )
        VALUES (
            %(place_name)s,
            %(region)s,
            %(latitude)s,
            %(longitude)s,
            %(start_date)s,
            %(end_date)s,
            %(hour_count)s,
            %(mean_wind_speed_10m_ms)s,
            %(mean_wind_speed_100m_ms)s,
            %(p90_wind_speed_100m_ms)s,
            %(max_wind_gust_10m_ms)s,
            %(mean_shortwave_radiation_wm2)s,
            %(total_shortwave_radiation_kwh_m2)s,
            %(total_sunshine_hours)s,
            %(wind_resource_score)s,
            %(solar_resource_score)s,
            ST_Transform(ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326), 2193)
        )
        ON CONFLICT (place_name, start_date, end_date)
        DO UPDATE SET
            mean_wind_speed_10m_ms = EXCLUDED.mean_wind_speed_10m_ms,
            mean_wind_speed_100m_ms = EXCLUDED.mean_wind_speed_100m_ms,
            p90_wind_speed_100m_ms = EXCLUDED.p90_wind_speed_100m_ms,
            max_wind_gust_10m_ms = EXCLUDED.max_wind_gust_10m_ms,
            mean_shortwave_radiation_wm2 = EXCLUDED.mean_shortwave_radiation_wm2,
            total_shortwave_radiation_kwh_m2 = EXCLUDED.total_shortwave_radiation_kwh_m2,
            total_sunshine_hours = EXCLUDED.total_sunshine_hours,
            wind_resource_score = EXCLUDED.wind_resource_score,
            solar_resource_score = EXCLUDED.solar_resource_score,
            geom = EXCLUDED.geom;
    """

    with psycopg2.connect(db_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(create_sql)
            for summary in summaries:
                cursor.execute(insert_sql, summary)
    return len(summaries)


def default_dates() -> tuple[str, str]:
    end = date.today() - timedelta(days=7)
    start = end - timedelta(days=365)
    return start.isoformat(), end.isoformat()


def parse_args() -> argparse.Namespace:
    start, end = default_dates()
    parser = argparse.ArgumentParser(description="Download historical wind and solar weather resource data.")
    parser.add_argument("--locations", type=Path, default=DEFAULT_LOCATIONS)
    parser.add_argument(
        "--city-sample",
        action="store_true",
        help="Use the smaller city sample location file instead of the extended rural/coastal analysis points.",
    )
    parser.add_argument("--max-locations", type=int, default=None, help="Limit processed locations for test runs.")
    parser.add_argument("--start-date", default=start)
    parser.add_argument("--end-date", default=end)
    parser.add_argument("--hourly-output", type=Path, default=DEFAULT_HOURLY_CSV)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--geojson-output", type=Path, default=DEFAULT_SUMMARY_GEOJSON)
    parser.add_argument("--insert-db", action="store_true")
    parser.add_argument("--db-dsn", default=default_db_dsn())
    parser.add_argument("--db-schema", default=os.getenv("POSTGIS_SCHEMA", "renewable_nz"))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--request-delay", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    location_path = CITY_SAMPLE_LOCATIONS if args.city_sample else args.locations
    locations = read_locations(location_path)
    if args.max_locations is not None:
        locations = locations[: args.max_locations]
    log("[start] Historical weather resource pipeline")
    log(f"[period] {args.start_date} to {args.end_date}")
    log(f"[source] locations={location_path}")
    log(f"[locations] {len(locations)}")

    all_hourly_rows: list[dict] = []
    summaries: list[dict] = []

    for index, location in enumerate(locations, start=1):
        log(f"[download] {index}/{len(locations)} {location.place_name}")
        payload = request_open_meteo(location, args.start_date, args.end_date, args.timeout)
        rows = rows_from_response(location, payload)
        all_hourly_rows.extend(rows)
        summaries.append(summarise_location(location, rows, args.start_date, args.end_date))
        time.sleep(args.request_delay)

    hourly_fields = [
        "place_name",
        "region",
        "latitude",
        "longitude",
        "time",
        *HOURLY_VARIABLES,
    ]
    summary_fields = list(summaries[0].keys()) if summaries else []
    write_csv(args.hourly_output, all_hourly_rows, hourly_fields)
    write_csv(args.summary_output, summaries, summary_fields)
    write_geojson(args.geojson_output, summaries)

    log(f"[output] hourly CSV: {args.hourly_output}")
    log(f"[output] summary CSV: {args.summary_output}")
    log(f"[output] summary GeoJSON: {args.geojson_output}")

    if args.insert_db:
        inserted = insert_summaries_to_postgis(summaries, args.db_dsn, args.db_schema)
        log(f"[db] upserted {inserted} rows into {args.db_schema}.weather_resource_summary")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
