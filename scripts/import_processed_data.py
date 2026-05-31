"""Import processed project outputs into PostGIS for VM deployment."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import psycopg2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEATHER_CSV = PROJECT_ROOT / "data" / "processed" / "weather_resource_summary.csv"
DEFAULT_SITE_GEOJSON = PROJECT_ROOT / "frontend" / "data" / "site_selection_candidates.geojson"
DEFAULT_GIR_GEOJSON = PROJECT_ROOT / "data" / "processed" / "renewable_energy_mentions.geojson"
FALLBACK_GIR_GEOJSON = PROJECT_ROOT / "frontend" / "data" / "gir_mentions.geojson"

ENERGY_TYPES = {"wind", "solar", "mixed", "renewable"}


def log(message: str) -> None:
    print(message, flush=True)


def default_db_dsn() -> str:
    return os.getenv(
        "DB_DSN",
        "host=localhost port=5432 dbname=renewable_nz user=postgres password=Postgres123",
    )


def quote_ident(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return f'"{value}"'


def none_if_blank(value: Any) -> Any:
    return None if value in ("", None) else value


def as_float(value: Any) -> float | None:
    value = none_if_blank(value)
    if value is None:
        return None
    return float(value)


def as_int(value: Any) -> int | None:
    value = none_if_blank(value)
    if value is None:
        return None
    return int(float(value))


def wait_for_postgis(db_dsn: str, attempts: int, delay: float) -> None:
    for attempt in range(1, attempts + 1):
        try:
            with psycopg2.connect(db_dsn) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT PostGIS_Version();")
                    version = cursor.fetchone()[0]
                    log(f"[db] connected to PostGIS {version}")
                    return
        except psycopg2.Error as exc:
            log(f"[db] waiting for PostGIS ({attempt}/{attempts}): {exc.pgerror or exc}")
            time.sleep(delay)
    raise RuntimeError("PostGIS did not become ready in time.")


def read_geojson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        log(f"[skip] missing {path}")
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("features") or [])


def coords_from_feature(feature: dict[str, Any]) -> tuple[float | None, float | None]:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    if geometry.get("type") == "Point" and len(coords) >= 2:
        return float(coords[1]), float(coords[0])
    props = feature.get("properties") or {}
    return as_float(props.get("latitude")), as_float(props.get("longitude"))


def replace_tables(conn, schema: str) -> None:
    q_schema = quote_ident(schema)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            TRUNCATE TABLE
                {q_schema}.gir_locations,
                {q_schema}.weather_resource_summary,
                {q_schema}.site_selection_candidates
            RESTART IDENTITY;
            """
        )
    conn.commit()
    log("[db] replaced processed-data tables")


def import_weather(conn, schema: str, path: Path) -> int:
    if not path.exists():
        log(f"[skip] missing {path}")
        return 0

    q_schema = quote_ident(schema)
    sql = f"""
        INSERT INTO {q_schema}.weather_resource_summary (
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
            data_source,
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
            %(data_source)s,
            ST_Transform(ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326), 2193)
        )
        ON CONFLICT (place_name, start_date, end_date) DO UPDATE SET
            region = EXCLUDED.region,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            hour_count = EXCLUDED.hour_count,
            mean_wind_speed_10m_ms = EXCLUDED.mean_wind_speed_10m_ms,
            mean_wind_speed_100m_ms = EXCLUDED.mean_wind_speed_100m_ms,
            p90_wind_speed_100m_ms = EXCLUDED.p90_wind_speed_100m_ms,
            max_wind_gust_10m_ms = EXCLUDED.max_wind_gust_10m_ms,
            mean_shortwave_radiation_wm2 = EXCLUDED.mean_shortwave_radiation_wm2,
            total_shortwave_radiation_kwh_m2 = EXCLUDED.total_shortwave_radiation_kwh_m2,
            total_sunshine_hours = EXCLUDED.total_sunshine_hours,
            wind_resource_score = EXCLUDED.wind_resource_score,
            solar_resource_score = EXCLUDED.solar_resource_score,
            data_source = EXCLUDED.data_source,
            geom = EXCLUDED.geom;
    """

    count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle, conn.cursor() as cursor:
        for row in csv.DictReader(handle):
            record = {
                "place_name": row["place_name"],
                "region": none_if_blank(row.get("region")),
                "latitude": as_float(row.get("latitude")),
                "longitude": as_float(row.get("longitude")),
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "hour_count": as_int(row.get("hour_count")),
                "mean_wind_speed_10m_ms": as_float(row.get("mean_wind_speed_10m_ms")),
                "mean_wind_speed_100m_ms": as_float(row.get("mean_wind_speed_100m_ms")),
                "p90_wind_speed_100m_ms": as_float(row.get("p90_wind_speed_100m_ms")),
                "max_wind_gust_10m_ms": as_float(row.get("max_wind_gust_10m_ms")),
                "mean_shortwave_radiation_wm2": as_float(row.get("mean_shortwave_radiation_wm2")),
                "total_shortwave_radiation_kwh_m2": as_float(row.get("total_shortwave_radiation_kwh_m2")),
                "total_sunshine_hours": as_float(row.get("total_sunshine_hours")),
                "wind_resource_score": as_float(row.get("wind_resource_score")),
                "solar_resource_score": as_float(row.get("solar_resource_score")),
                "data_source": row.get("data_source") or "Open-Meteo Historical Weather API",
            }
            if record["latitude"] is None or record["longitude"] is None:
                continue
            cursor.execute(sql, record)
            count += 1
    conn.commit()
    log(f"[db] imported {count} weather resource rows")
    return count


def import_gir(conn, schema: str, primary_path: Path, fallback_path: Path) -> int:
    path = primary_path if primary_path.exists() else fallback_path
    features = read_geojson(path)
    if not features:
        return 0

    q_schema = quote_ident(schema)
    sql = f"""
        INSERT INTO {q_schema}.gir_locations (
            article_title,
            place_name,
            latitude,
            longitude,
            energy_type,
            source_url,
            confidence,
            geom
        )
        VALUES (
            %(article_title)s,
            %(place_name)s,
            %(latitude)s,
            %(longitude)s,
            %(energy_type)s,
            %(source_url)s,
            %(confidence)s,
            ST_Transform(ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326), 2193)
        );
    """

    count = 0
    with conn.cursor() as cursor:
        for feature in features:
            props = feature.get("properties") or {}
            lat, lon = coords_from_feature(feature)
            place_name = none_if_blank(props.get("place_name"))
            title = none_if_blank(props.get("article_title") or props.get("title"))
            if lat is None or lon is None or not place_name or not title:
                continue
            energy_type = str(props.get("energy_type") or "renewable").lower()
            if energy_type not in ENERGY_TYPES:
                energy_type = "renewable"
            cursor.execute(
                sql,
                {
                    "article_title": title,
                    "place_name": place_name,
                    "latitude": lat,
                    "longitude": lon,
                    "energy_type": energy_type,
                    "source_url": none_if_blank(props.get("source_url")),
                    "confidence": as_float(props.get("confidence")) or 0.8,
                },
            )
            count += 1
    conn.commit()
    log(f"[db] imported {count} GIR rows")
    return count


def import_site_candidates(conn, schema: str, path: Path) -> int:
    features = read_geojson(path)
    if not features:
        return 0

    q_schema = quote_ident(schema)
    sql = f"""
        INSERT INTO {q_schema}.site_selection_candidates (
            rank,
            energy_type,
            candidate_name,
            region,
            final_score,
            weather_resource_score,
            grid_connection_score,
            gir_evidence_score,
            interpolation_confidence,
            distance_to_transmission_km,
            mean_wind_speed_100m_ms,
            p90_wind_speed_100m_ms,
            total_shortwave_radiation_kwh_m2,
            total_sunshine_hours,
            nearest_weather_point,
            gir_mentions_nearby,
            candidate_source,
            score_formula,
            geom
        )
        VALUES (
            %(rank)s,
            %(energy_type)s,
            %(candidate_name)s,
            %(region)s,
            %(final_score)s,
            %(weather_resource_score)s,
            %(grid_connection_score)s,
            %(gir_evidence_score)s,
            %(interpolation_confidence)s,
            %(distance_to_transmission_km)s,
            %(mean_wind_speed_100m_ms)s,
            %(p90_wind_speed_100m_ms)s,
            %(total_shortwave_radiation_kwh_m2)s,
            %(total_sunshine_hours)s,
            %(nearest_weather_point)s,
            %(gir_mentions_nearby)s,
            %(candidate_source)s,
            %(score_formula)s,
            ST_Transform(ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326), 2193)
        )
        ON CONFLICT (energy_type, rank) DO UPDATE SET
            candidate_name = EXCLUDED.candidate_name,
            region = EXCLUDED.region,
            final_score = EXCLUDED.final_score,
            weather_resource_score = EXCLUDED.weather_resource_score,
            grid_connection_score = EXCLUDED.grid_connection_score,
            gir_evidence_score = EXCLUDED.gir_evidence_score,
            interpolation_confidence = EXCLUDED.interpolation_confidence,
            distance_to_transmission_km = EXCLUDED.distance_to_transmission_km,
            mean_wind_speed_100m_ms = EXCLUDED.mean_wind_speed_100m_ms,
            p90_wind_speed_100m_ms = EXCLUDED.p90_wind_speed_100m_ms,
            total_shortwave_radiation_kwh_m2 = EXCLUDED.total_shortwave_radiation_kwh_m2,
            total_sunshine_hours = EXCLUDED.total_sunshine_hours,
            nearest_weather_point = EXCLUDED.nearest_weather_point,
            gir_mentions_nearby = EXCLUDED.gir_mentions_nearby,
            candidate_source = EXCLUDED.candidate_source,
            score_formula = EXCLUDED.score_formula,
            geom = EXCLUDED.geom;
    """

    count = 0
    with conn.cursor() as cursor:
        for feature in features:
            props = feature.get("properties") or {}
            lat, lon = coords_from_feature(feature)
            if lat is None or lon is None:
                continue
            cursor.execute(
                sql,
                {
                    "rank": as_int(props.get("rank")),
                    "energy_type": str(props.get("energy_type") or "").lower(),
                    "candidate_name": props.get("candidate_name"),
                    "region": none_if_blank(props.get("region")),
                    "final_score": as_float(props.get("final_score")),
                    "weather_resource_score": as_float(props.get("weather_resource_score")),
                    "grid_connection_score": as_float(props.get("grid_connection_score")),
                    "gir_evidence_score": as_float(props.get("gir_evidence_score")),
                    "interpolation_confidence": as_float(props.get("interpolation_confidence")),
                    "distance_to_transmission_km": as_float(props.get("distance_to_transmission_km")),
                    "mean_wind_speed_100m_ms": as_float(props.get("mean_wind_speed_100m_ms")),
                    "p90_wind_speed_100m_ms": as_float(props.get("p90_wind_speed_100m_ms")),
                    "total_shortwave_radiation_kwh_m2": as_float(props.get("total_shortwave_radiation_kwh_m2")),
                    "total_sunshine_hours": as_float(props.get("total_sunshine_hours")),
                    "nearest_weather_point": none_if_blank(props.get("nearest_weather_point")),
                    "gir_mentions_nearby": as_int(props.get("gir_mentions_nearby")) or 0,
                    "candidate_source": none_if_blank(props.get("candidate_source")),
                    "score_formula": none_if_blank(props.get("score_formula")),
                    "latitude": lat,
                    "longitude": lon,
                },
            )
            count += 1
    conn.commit()
    log(f"[db] imported {count} site candidate rows")
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import processed WebGIS outputs into PostGIS.")
    parser.add_argument("--db-dsn", default=default_db_dsn())
    parser.add_argument("--schema", default=os.getenv("POSTGIS_SCHEMA", "renewable_nz"))
    parser.add_argument("--weather-csv", type=Path, default=DEFAULT_WEATHER_CSV)
    parser.add_argument("--site-geojson", type=Path, default=DEFAULT_SITE_GEOJSON)
    parser.add_argument("--gir-geojson", type=Path, default=DEFAULT_GIR_GEOJSON)
    parser.add_argument("--fallback-gir-geojson", type=Path, default=FALLBACK_GIR_GEOJSON)
    parser.add_argument("--replace", action="store_true", help="Truncate processed-data tables before import.")
    parser.add_argument("--wait-attempts", type=int, default=30)
    parser.add_argument("--wait-delay", type=float, default=2.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wait_for_postgis(args.db_dsn, args.wait_attempts, args.wait_delay)

    with psycopg2.connect(args.db_dsn) as conn:
        if args.replace:
            replace_tables(conn, args.schema)
        import_weather(conn, args.schema, args.weather_csv)
        import_gir(conn, args.schema, args.gir_geojson, args.fallback_gir_geojson)
        import_site_candidates(conn, args.schema, args.site_geojson)

    log("[done] processed data import complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
