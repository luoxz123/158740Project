"""Prepare and optionally import Transpower transmission line data.

Source:
Transpower Open Data, TransmissionLines FeatureServer.
The source data is published in EPSG:4326 by the download step used for this
project and is inserted into PostGIS as EPSG:2193.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = PROJECT_ROOT / "data" / "raw" / "transpower_transmission_lines.geojson"
DEFAULT_FRONTEND = PROJECT_ROOT / "frontend" / "data" / "transmission_lines.geojson"
SOURCE_URL = (
    "https://services3.arcgis.com/AkUq3zcWf7TVqyR9/arcgis/rest/services/"
    "TransmissionLines/FeatureServer/0/query"
)
SOURCE_ATTRIBUTION = "Transpower Open Data TransmissionLines FeatureServer (CC BY 4.0)"


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


def download_source(path: Path, timeout: int) -> None:
    if requests is None:
        raise RuntimeError("Download requires requests. Install with: py -m pip install requests")

    params = {
        "where": "status='COMMISSIONED'",
        "outFields": "MXLOCATION,designvolt,status,description,type,Symbol",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": "2000",
    }
    url = f"{SOURCE_URL}?{urllib.parse.urlencode(params)}"
    log(f"[download] {url}")
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(response.text, encoding="utf-8")
    log(f"[download] wrote {path}")


def parse_voltage(value: Any, symbol: str | None = None) -> int | None:
    for candidate in [value, symbol]:
        if candidate in (None, ""):
            continue
        match = re.search(r"\d+", str(candidate))
        if match:
            return int(match.group(0))
    return None


def clean_point(point: Any) -> list[float] | None:
    if not isinstance(point, list | tuple) or len(point) < 2:
        return None
    try:
        lon = float(point[0])
        lat = float(point[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lon) or not math.isfinite(lat):
        return None
    return [lon, lat]


def same_point(first: list[float], second: list[float]) -> bool:
    return abs(first[0] - second[0]) < 1e-12 and abs(first[1] - second[1]) < 1e-12


def clean_line(coords: Any) -> list[list[float]] | None:
    if not isinstance(coords, list):
        return None

    cleaned: list[list[float]] = []
    for raw_point in coords:
        point = clean_point(raw_point)
        if point is None:
            continue
        if not cleaned or not same_point(cleaned[-1], point):
            cleaned.append(point)

    unique_points = {(point[0], point[1]) for point in cleaned}
    if len(cleaned) < 2 or len(unique_points) < 2:
        return None
    return cleaned


def point_segment_distance(point: list[float], start: list[float], end: list[float]) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    nearest_x = ax + t * dx
    nearest_y = ay + t * dy
    return ((px - nearest_x) ** 2 + (py - nearest_y) ** 2) ** 0.5


def simplify_line(coords: list[list[float]], tolerance: float) -> list[list[float]]:
    if tolerance <= 0 or len(coords) <= 2:
        return coords

    max_distance = -1.0
    split_index = 0
    start = coords[0]
    end = coords[-1]
    for index in range(1, len(coords) - 1):
        distance = point_segment_distance(coords[index], start, end)
        if distance > max_distance:
            max_distance = distance
            split_index = index

    if max_distance > tolerance:
        left = simplify_line(coords[: split_index + 1], tolerance)
        right = simplify_line(coords[split_index:], tolerance)
        return left[:-1] + right
    return [start, end]


def simplify_geometry(geometry: dict[str, Any], tolerance: float) -> dict[str, Any]:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geom_type == "LineString":
        line = clean_line(coordinates)
        if line is None:
            return {}
        simplified = simplify_line(line, tolerance) if tolerance > 0 else line
        simplified = clean_line(simplified)
        return {**geometry, "coordinates": simplified} if simplified else {}
    if geom_type == "MultiLineString":
        lines = []
        for line in coordinates:
            cleaned = clean_line(line)
            if cleaned is None:
                continue
            simplified = simplify_line(cleaned, tolerance) if tolerance > 0 else cleaned
            simplified = clean_line(simplified)
            if simplified:
                lines.append(simplified)
        if not lines:
            return {}
        return {
            **geometry,
            "coordinates": lines,
        }
    return {}


def feature_name(props: dict[str, Any]) -> str:
    description = str(props.get("description") or "").strip()
    mxlocation = str(props.get("MXLOCATION") or "").strip()
    if description and description.lower() not in {"none", "null"}:
        return description
    if mxlocation:
        return mxlocation
    return "Transpower transmission line"


def normalise_features(source: dict[str, Any], simplify_tolerance: float) -> dict[str, Any]:
    output_features: list[dict[str, Any]] = []
    for index, feature in enumerate(source.get("features") or [], start=1):
        geometry = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        if geometry.get("type") not in {"LineString", "MultiLineString"}:
            continue

        geometry = simplify_geometry(geometry, simplify_tolerance)
        if not geometry:
            continue

        voltage = parse_voltage(props.get("designvolt"), props.get("Symbol"))
        mxlocation = str(props.get("MXLOCATION") or f"transpower-{index:03d}").strip()
        name = feature_name(props)
        output_features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": f"transpower-{index:03d}",
                    "name": name,
                    "line_name": name,
                    "mxlocation": mxlocation,
                    "voltage_kv": voltage,
                    "operator": "Transpower",
                    "operator_name": "Transpower",
                    "line_type": props.get("type"),
                    "status": props.get("status"),
                    "symbol": props.get("Symbol"),
                    "data_source": SOURCE_ATTRIBUTION,
                },
                "geometry": geometry,
            }
        )

    return {
        "type": "FeatureCollection",
        "name": "transmission_lines",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": output_features,
    }


def write_frontend_geojson(raw_path: Path, output_path: Path, simplify_tolerance: float) -> dict[str, Any]:
    source = json.loads(raw_path.read_text(encoding="utf-8"))
    normalised = normalise_features(source, simplify_tolerance)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalised, indent=2), encoding="utf-8")
    log(f"[output] wrote {len(normalised['features'])} transmission lines to {output_path}")
    return normalised


def insert_to_postgis(features: list[dict[str, Any]], db_dsn: str, schema: str) -> int:
    if psycopg2 is None:
        raise RuntimeError("PostGIS insertion requires psycopg2-binary.")

    q_schema = quote_ident(schema)
    sql = f"""
        INSERT INTO {q_schema}.transmission_lines (
            line_name,
            voltage_kv,
            operator_name,
            data_source,
            geom
        )
        VALUES (
            %(line_name)s,
            %(voltage_kv)s,
            %(operator_name)s,
            %(data_source)s,
            ST_Multi(
                ST_CollectionExtract(
                    ST_MakeValid(
                        ST_RemoveRepeatedPoints(
                            ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%(geometry)s), 4326), 2193)
                        )
                    ),
                    2
                )
            )
        );
    """

    with psycopg2.connect(db_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {q_schema}.transmission_lines RESTART IDENTITY CASCADE;")
            for feature in features:
                props = feature["properties"]
                cursor.execute(
                    sql,
                    {
                        "line_name": props["line_name"],
                        "voltage_kv": props.get("voltage_kv"),
                        "operator_name": props.get("operator_name") or "Transpower",
                        "data_source": props.get("data_source") or SOURCE_ATTRIBUTION,
                        "geometry": json.dumps(feature["geometry"]),
                    },
                )
    log(f"[db] inserted {len(features)} rows into {schema}.transmission_lines")
    return len(features)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Transpower transmission lines for the WebGIS project.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output", type=Path, default=DEFAULT_FRONTEND)
    parser.add_argument("--download", action="store_true", help="Download the latest source GeoJSON before processing.")
    parser.add_argument("--download-timeout", type=int, default=60)
    parser.add_argument(
        "--simplify-tolerance-deg",
        type=float,
        default=0.002,
        help="Douglas-Peucker simplification tolerance in degrees for frontend and analysis output.",
    )
    parser.add_argument("--insert-db", action="store_true")
    parser.add_argument("--db-dsn", default=default_db_dsn())
    parser.add_argument("--db-schema", default=os.getenv("POSTGIS_SCHEMA", "renewable_nz"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.download or not args.raw.exists():
        download_source(args.raw, args.download_timeout)

    normalised = write_frontend_geojson(args.raw, args.output, args.simplify_tolerance_deg)

    if args.insert_db:
        insert_to_postgis(normalised["features"], args.db_dsn, args.db_schema)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
