"""Rank wind farm and solar farm candidate sites.

The analysis uses already collected project data:
- 87-point weather resource summaries from Open-Meteo
- transmission line GeoJSON
- GIR renewable/weather/news mentions

Weather values are interpolated with inverse distance weighting (IDW). Candidate
locations include the original weather points and midpoints between nearby
weather points, which creates simple rural/coastal corridor candidates without
requiring paid national VCSN data.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEATHER_SUMMARY = PROJECT_ROOT / "data" / "processed" / "weather_resource_summary.csv"
DEFAULT_TRANSMISSION = PROJECT_ROOT / "frontend" / "data" / "transmission_lines.geojson"
DEFAULT_GIR = PROJECT_ROOT / "data" / "processed" / "renewable_energy_mentions.geojson"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "site_selection_top10.csv"
DEFAULT_WIND_CSV = PROJECT_ROOT / "data" / "processed" / "wind_farm_candidates_top10.csv"
DEFAULT_SOLAR_CSV = PROJECT_ROOT / "data" / "processed" / "solar_farm_candidates_top10.csv"
DEFAULT_OUTPUT_GEOJSON = PROJECT_ROOT / "frontend" / "data" / "site_selection_candidates.geojson"

WIND_KEYWORDS = {"wind", "windy", "gale", "gust", "gusts", "turbine", "wind farm", "strong wind"}
SOLAR_KEYWORDS = {"solar", "sun", "sunshine", "photovoltaic", "pv", "solar farm"}


@dataclass
class WeatherPoint:
    place_name: str
    region: str
    latitude: float
    longitude: float
    values: dict[str, float]


@dataclass
class CandidatePoint:
    candidate_name: str
    region: str
    latitude: float
    longitude: float
    source: str


@dataclass
class GirMention:
    title: str
    place_name: str
    energy_type: str
    latitude: float
    longitude: float
    confidence: float
    source_url: str


def log(message: str) -> None:
    print(message, flush=True)


def safe_float(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def to_local_xy_km(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    x = (lon - origin_lon) * 111.320 * math.cos(math.radians(origin_lat))
    y = (lat - origin_lat) * 110.574
    return x, y


def point_segment_distance_km(
    point_lat: float,
    point_lon: float,
    start: list[float],
    end: list[float],
) -> float:
    px, py = 0.0, 0.0
    ax, ay = to_local_xy_km(start[1], start[0], point_lat, point_lon)
    bx, by = to_local_xy_km(end[1], end[0], point_lat, point_lon)
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    nearest_x = ax + t * dx
    nearest_y = ay + t * dy
    return math.hypot(px - nearest_x, py - nearest_y)


def load_weather_points(path: Path) -> list[WeatherPoint]:
    points: list[WeatherPoint] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            points.append(
                WeatherPoint(
                    place_name=row["place_name"],
                    region=row.get("region", ""),
                    latitude=safe_float(row.get("latitude")),
                    longitude=safe_float(row.get("longitude")),
                    values={
                        "mean_wind_speed_10m_ms": safe_float(row.get("mean_wind_speed_10m_ms")),
                        "mean_wind_speed_100m_ms": safe_float(row.get("mean_wind_speed_100m_ms")),
                        "p90_wind_speed_100m_ms": safe_float(row.get("p90_wind_speed_100m_ms")),
                        "max_wind_gust_10m_ms": safe_float(row.get("max_wind_gust_10m_ms")),
                        "mean_shortwave_radiation_wm2": safe_float(row.get("mean_shortwave_radiation_wm2")),
                        "total_shortwave_radiation_kwh_m2": safe_float(row.get("total_shortwave_radiation_kwh_m2")),
                        "total_sunshine_hours": safe_float(row.get("total_sunshine_hours")),
                        "wind_resource_score": safe_float(row.get("wind_resource_score")),
                        "solar_resource_score": safe_float(row.get("solar_resource_score")),
                    },
                )
            )
    return points


def load_transmission_segments(path: Path) -> list[tuple[list[float], list[float]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    segments: list[tuple[list[float], list[float]]] = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates") or []
        lines = [coordinates] if geom_type == "LineString" else coordinates if geom_type == "MultiLineString" else []
        for line in lines:
            for index in range(len(line) - 1):
                segments.append((line[index], line[index + 1]))
    return segments


def load_gir_mentions(path: Path) -> list[GirMention]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    mentions: list[GirMention] = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        mentions.append(
            GirMention(
                title=props.get("article_title", ""),
                place_name=props.get("place_name", ""),
                energy_type=props.get("energy_type", ""),
                latitude=safe_float(props.get("latitude"), coords[1]),
                longitude=safe_float(props.get("longitude"), coords[0]),
                confidence=safe_float(props.get("confidence"), 0.5),
                source_url=props.get("source_url", ""),
            )
        )
    return mentions


def generate_candidates(
    weather_points: list[WeatherPoint],
    include_midpoints: bool,
    max_midpoint_distance_km: float,
) -> list[CandidatePoint]:
    candidates: list[CandidatePoint] = [
        CandidatePoint(
            candidate_name=point.place_name,
            region=point.region,
            latitude=point.latitude,
            longitude=point.longitude,
            source="weather_point",
        )
        for point in weather_points
    ]
    seen = {(round(point.latitude, 4), round(point.longitude, 4)) for point in weather_points}

    if include_midpoints:
        for left_index, left in enumerate(weather_points):
            for right in weather_points[left_index + 1 :]:
                distance = haversine_km(left.latitude, left.longitude, right.latitude, right.longitude)
                if distance > max_midpoint_distance_km:
                    continue
                lat = (left.latitude + right.latitude) / 2
                lon = (left.longitude + right.longitude) / 2
                key = (round(lat, 4), round(lon, 4))
                if key in seen:
                    continue
                seen.add(key)
                region = left.region if left.region == right.region else f"{left.region} / {right.region}".strip(" /")
                candidates.append(
                    CandidatePoint(
                        candidate_name=f"{left.place_name} - {right.place_name} corridor",
                        region=region,
                        latitude=lat,
                        longitude=lon,
                        source="idw_midpoint",
                    )
                )
    return candidates


def nearest_weather_distance(candidate: CandidatePoint, weather_points: list[WeatherPoint]) -> tuple[str, float]:
    nearest_name = ""
    nearest_distance = float("inf")
    for point in weather_points:
        distance = haversine_km(candidate.latitude, candidate.longitude, point.latitude, point.longitude)
        if distance < nearest_distance:
            nearest_name = point.place_name
            nearest_distance = distance
    return nearest_name, nearest_distance


def idw_value(
    candidate: CandidatePoint,
    weather_points: list[WeatherPoint],
    field: str,
    max_neighbors: int,
    power: float,
) -> float:
    distances = []
    for point in weather_points:
        value = point.values.get(field)
        if value is None:
            continue
        distance = haversine_km(candidate.latitude, candidate.longitude, point.latitude, point.longitude)
        if distance < 0.01:
            return value
        distances.append((distance, value))

    selected = sorted(distances, key=lambda item: item[0])[:max_neighbors]
    if not selected:
        return 0.0
    weighted_sum = 0.0
    weight_total = 0.0
    for distance, value in selected:
        weight = 1.0 / max(distance, 0.1) ** power
        weighted_sum += value * weight
        weight_total += weight
    return weighted_sum / weight_total


def transmission_distance_km(candidate: CandidatePoint, segments: list[tuple[list[float], list[float]]]) -> float:
    if not segments:
        return 999.0
    return min(
        point_segment_distance_km(candidate.latitude, candidate.longitude, start, end)
        for start, end in segments
    )


def grid_connection_score(distance_km: float) -> float:
    if distance_km <= 10:
        return 100.0
    if distance_km >= 130:
        return 0.0
    return clamp(100.0 - ((distance_km - 10.0) / 120.0) * 100.0)


def keyword_match_score(text: str, energy_type: str) -> float:
    lowered = text.lower()
    keywords = WIND_KEYWORDS if energy_type == "wind" else SOLAR_KEYWORDS
    return 1.0 if any(keyword in lowered for keyword in keywords) else 0.0


def is_low_quality_gir_mention(mention: GirMention) -> bool:
    title = mention.title.strip().lower()
    source_url = mention.source_url.lower()
    return title.startswith("latest from ") or "/author/" in source_url


def gir_match_weight(mention: GirMention, energy_type: str) -> float:
    text = f"{mention.title} {mention.place_name} {mention.energy_type}"
    keyword_weight = keyword_match_score(text, energy_type)
    if mention.energy_type == energy_type:
        return 1.0
    if mention.energy_type in {"mixed", "renewable"}:
        return max(0.65, keyword_weight)
    return max(0.2, keyword_weight)


def gir_evidence(candidate: CandidatePoint, mentions: list[GirMention], energy_type: str, radius_km: float) -> tuple[float, int, str]:
    score = 0.0
    nearby_titles: list[tuple[float, str]] = []
    count = 0
    for mention in mentions:
        if is_low_quality_gir_mention(mention):
            continue
        distance = haversine_km(candidate.latitude, candidate.longitude, mention.latitude, mention.longitude)
        if distance > radius_km:
            continue
        count += 1
        decay = max(0.0, 1.0 - distance / radius_km)
        match_weight = gir_match_weight(mention, energy_type)
        score += 75.0 * mention.confidence * match_weight * decay
        nearby_titles.append((distance, mention.title or mention.place_name))

    titles = "; ".join(title for _, title in sorted(nearby_titles)[:3])
    return clamp(score), count, titles


def interpolation_confidence(nearest_distance_km: float) -> float:
    if nearest_distance_km <= 1:
        return 100.0
    if nearest_distance_km >= 90:
        return 20.0
    return clamp(100.0 - ((nearest_distance_km - 1.0) / 89.0) * 80.0, 20.0, 100.0)


def score_candidates(
    candidates: list[CandidatePoint],
    weather_points: list[WeatherPoint],
    transmission_segments: list[tuple[list[float], list[float]]],
    gir_mentions: list[GirMention],
    energy_type: str,
    max_neighbors: int,
    idw_power: float,
    gir_radius_km: float,
) -> list[dict]:
    scored: list[dict] = []
    resource_field = "wind_resource_score" if energy_type == "wind" else "solar_resource_score"

    for candidate in candidates:
        resource_score = idw_value(candidate, weather_points, resource_field, max_neighbors, idw_power)
        mean_wind100 = idw_value(candidate, weather_points, "mean_wind_speed_100m_ms", max_neighbors, idw_power)
        p90_wind100 = idw_value(candidate, weather_points, "p90_wind_speed_100m_ms", max_neighbors, idw_power)
        radiation = idw_value(candidate, weather_points, "total_shortwave_radiation_kwh_m2", max_neighbors, idw_power)
        sunshine = idw_value(candidate, weather_points, "total_sunshine_hours", max_neighbors, idw_power)
        grid_distance = transmission_distance_km(candidate, transmission_segments)
        grid_score = grid_connection_score(grid_distance)
        nearest_name, nearest_distance = nearest_weather_distance(candidate, weather_points)
        confidence_score = interpolation_confidence(nearest_distance)
        gir_score, gir_count, gir_titles = gir_evidence(candidate, gir_mentions, energy_type, gir_radius_km)

        final_score = (
            0.55 * resource_score
            + 0.25 * grid_score
            + 0.15 * gir_score
            + 0.05 * confidence_score
        )

        scored.append(
            {
                "energy_type": energy_type,
                "candidate_name": candidate.candidate_name,
                "region": candidate.region,
                "latitude": round(candidate.latitude, 6),
                "longitude": round(candidate.longitude, 6),
                "final_score": round(final_score, 1),
                "weather_resource_score": round(resource_score, 1),
                "grid_connection_score": round(grid_score, 1),
                "gir_evidence_score": round(gir_score, 1),
                "interpolation_confidence": round(confidence_score, 1),
                "distance_to_transmission_km": round(grid_distance, 2),
                "mean_wind_speed_100m_ms": round(mean_wind100, 3),
                "p90_wind_speed_100m_ms": round(p90_wind100, 3),
                "total_shortwave_radiation_kwh_m2": round(radiation, 3),
                "total_sunshine_hours": round(sunshine, 2),
                "nearest_weather_point": nearest_name,
                "nearest_weather_distance_km": round(nearest_distance, 2),
                "gir_mentions_nearby": gir_count,
                "gir_evidence_titles": gir_titles,
                "candidate_source": candidate.source,
                "score_formula": "55% resource + 25% transmission proximity + 15% GIR evidence + 5% interpolation confidence",
            }
        )

    ranked = sorted(scored, key=lambda item: item["final_score"], reverse=True)
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return ranked


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_geojson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for row in rows:
        props = dict(row)
        lat = props.pop("latitude")
        lon = props.pop("longitude")
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
        )
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "site_selection_candidates",
                "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def validate_sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid SQL identifier: {value}")
    return value


def default_db_dsn() -> str:
    if os.getenv("POSTGIS_DSN"):
        return os.environ["POSTGIS_DSN"]
    password = os.getenv("POSTGIS_PASSWORD", "")
    parts = [
        f"host={os.getenv('POSTGIS_HOST', 'localhost')}",
        f"port={os.getenv('POSTGIS_PORT', '5432')}",
        f"dbname={os.getenv('POSTGIS_DB', 'renewable_nz')}",
        f"user={os.getenv('POSTGIS_USER', 'postgres')}",
    ]
    if password:
        parts.append(f"password={password}")
    return " ".join(parts)


def insert_candidates_to_postgis(rows: list[dict], db_dsn: str, schema: str) -> int:
    if psycopg2 is None:
        raise RuntimeError("PostGIS insertion requires psycopg2-binary.")
    schema = validate_sql_identifier(schema)

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {schema}.site_selection_candidates (
            id SERIAL PRIMARY KEY,
            rank INTEGER NOT NULL,
            energy_type VARCHAR(20) NOT NULL,
            candidate_name VARCHAR(220) NOT NULL,
            region VARCHAR(160),
            final_score NUMERIC(5,1),
            weather_resource_score NUMERIC(5,1),
            grid_connection_score NUMERIC(5,1),
            gir_evidence_score NUMERIC(5,1),
            interpolation_confidence NUMERIC(5,1),
            distance_to_transmission_km NUMERIC(8,2),
            mean_wind_speed_100m_ms NUMERIC(8,3),
            p90_wind_speed_100m_ms NUMERIC(8,3),
            total_shortwave_radiation_kwh_m2 NUMERIC(12,3),
            total_sunshine_hours NUMERIC(12,2),
            nearest_weather_point VARCHAR(160),
            gir_mentions_nearby INTEGER,
            candidate_source VARCHAR(40),
            score_formula TEXT,
            geom geometry(POINT, 2193) NOT NULL,
            UNIQUE (energy_type, rank)
        );
        CREATE INDEX IF NOT EXISTS site_selection_candidates_geom_gix
            ON {schema}.site_selection_candidates USING GIST (geom);
    """
    insert_sql = f"""
        INSERT INTO {schema}.site_selection_candidates (
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
        ON CONFLICT (energy_type, rank)
        DO UPDATE SET
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

    with psycopg2.connect(db_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(create_sql)
            cursor.execute(f"DELETE FROM {schema}.site_selection_candidates")
            for row in rows:
                cursor.execute(insert_sql, row)
    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank wind and solar farm candidate sites from 87-point weather data.")
    parser.add_argument("--weather-summary", type=Path, default=DEFAULT_WEATHER_SUMMARY)
    parser.add_argument("--transmission", type=Path, default=DEFAULT_TRANSMISSION)
    parser.add_argument("--gir", type=Path, default=DEFAULT_GIR)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--wind-output-csv", type=Path, default=DEFAULT_WIND_CSV)
    parser.add_argument("--solar-output-csv", type=Path, default=DEFAULT_SOLAR_CSV)
    parser.add_argument("--output-geojson", type=Path, default=DEFAULT_OUTPUT_GEOJSON)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--include-midpoints", action="store_true", default=True)
    parser.add_argument("--no-midpoints", dest="include_midpoints", action="store_false")
    parser.add_argument("--max-midpoint-distance-km", type=float, default=110.0)
    parser.add_argument("--idw-neighbors", type=int, default=8)
    parser.add_argument("--idw-power", type=float, default=2.0)
    parser.add_argument("--gir-radius-km", type=float, default=120.0)
    parser.add_argument("--insert-db", action="store_true")
    parser.add_argument("--db-dsn", default=default_db_dsn())
    parser.add_argument("--db-schema", default=os.getenv("POSTGIS_SCHEMA", "renewable_nz"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    weather_points = load_weather_points(args.weather_summary)
    transmission_segments = load_transmission_segments(args.transmission)
    gir_mentions = load_gir_mentions(args.gir)

    log("[start] Site selection analysis")
    log(f"[input] weather points={len(weather_points)}")
    log(f"[input] transmission segments={len(transmission_segments)}")
    log(f"[input] GIR mentions={len(gir_mentions)}")

    candidates = generate_candidates(
        weather_points=weather_points,
        include_midpoints=args.include_midpoints,
        max_midpoint_distance_km=args.max_midpoint_distance_km,
    )
    log(f"[analysis] candidate points={len(candidates)}")

    wind_ranked = score_candidates(
        candidates=candidates,
        weather_points=weather_points,
        transmission_segments=transmission_segments,
        gir_mentions=gir_mentions,
        energy_type="wind",
        max_neighbors=args.idw_neighbors,
        idw_power=args.idw_power,
        gir_radius_km=args.gir_radius_km,
    )[: args.top_n]
    solar_ranked = score_candidates(
        candidates=candidates,
        weather_points=weather_points,
        transmission_segments=transmission_segments,
        gir_mentions=gir_mentions,
        energy_type="solar",
        max_neighbors=args.idw_neighbors,
        idw_power=args.idw_power,
        gir_radius_km=args.gir_radius_km,
    )[: args.top_n]

    combined = wind_ranked + solar_ranked
    write_csv(args.wind_output_csv, wind_ranked)
    write_csv(args.solar_output_csv, solar_ranked)
    write_csv(args.output_csv, combined)
    write_geojson(args.output_geojson, combined)

    log(f"[output] wind top {args.top_n}: {args.wind_output_csv}")
    log(f"[output] solar top {args.top_n}: {args.solar_output_csv}")
    log(f"[output] combined CSV: {args.output_csv}")
    log(f"[output] frontend GeoJSON: {args.output_geojson}")

    if args.insert_db:
        inserted = insert_candidates_to_postgis(combined, args.db_dsn, args.db_schema)
        log(f"[db] upserted {inserted} rows into {args.db_schema}.site_selection_candidates")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
