"""NIWA / Earth Sciences NZ VCSN weather resource pipeline.

This script imports VCSN daily CSV files and summarises solar radiation and wind
speed for every VCSN point available in the input data.

Expected VCSN variables:
- Station
- Date
- WindSpeed, daily mean wind speed at 10 m, m/s
- Radiation, daily accumulated global solar radiation, MJ/m2

The script accepts one large CSV, a folder of CSV files, ZIP files, or GZIP CSVs.
If latitude/longitude are not present in the data rows, provide a station
metadata CSV with station, latitude, longitude, and optional region columns.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import re
import statistics
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, TextIO

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "vcsn"
DEFAULT_DOWNLOAD_DIR = PROJECT_ROOT / "data" / "raw" / "vcsn"
DEFAULT_SUMMARY_CSV = PROJECT_ROOT / "data" / "processed" / "vcsn_weather_resource_summary.csv"
DEFAULT_SUMMARY_GEOJSON = PROJECT_ROOT / "frontend" / "data" / "weather_resource_summary.geojson"
DATAHUB_FILE_API = "https://d17fc0a885.execute-api.ap-southeast-2.amazonaws.com/dev/api/data-files/{file_id}"
DATAHUB_FILES_API = "https://d17fc0a885.execute-api.ap-southeast-2.amazonaws.com/dev/api/data-files"

STATION_ALIASES = {"station", "networknumber", "networkno", "vcsn", "vcsnstation", "agent", "agentnumber"}
DATE_ALIASES = {"date", "observationtimeutc", "time", "datetime"}
LAT_ALIASES = {"lat", "latitude", "y"}
LON_ALIASES = {"lon", "long", "longitude", "x"}
REGION_ALIASES = {"region", "regionalcouncil", "area"}
NAME_ALIASES = {"name", "placename", "stationname", "location"}
WIND_ALIASES = {"windspeed", "meanwindspeed", "wind", "windms", "windmps"}
RADIATION_ALIASES = {"radiation", "globalsolarradiation", "solarradiation", "rad", "radiationmjm2"}


@dataclass
class StationMeta:
    station_id: str
    place_name: str
    latitude: float | None = None
    longitude: float | None = None
    region: str = ""


@dataclass
class StationAggregate:
    station_id: str
    place_name: str
    region: str = ""
    latitude: float | None = None
    longitude: float | None = None
    dates: list[str] = field(default_factory=list)
    wind10_values: list[float] = field(default_factory=list)
    radiation_mj_values: list[float] = field(default_factory=list)


def log(message: str) -> None:
    print(message, flush=True)


def normalise(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def safe_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def safe_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if match:
        return match.group(0)
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return value.strip()[:10]


def first_column(fieldnames: Iterable[str], aliases: set[str]) -> str | None:
    for fieldname in fieldnames:
        if normalise(fieldname) in aliases:
            return fieldname
    return None


def value_for(row: dict[str, str], column: str | None) -> str | None:
    if not column:
        return None
    value = row.get(column)
    return value.strip() if isinstance(value, str) else value


def parse_metadata_line(line: str, metadata: dict[str, str]) -> None:
    parts = [part.strip() for part in re.split(r"[:,]", line, maxsplit=1)]
    if len(parts) != 2:
        return
    key = normalise(parts[0])
    value = parts[1].strip()
    if key in STATION_ALIASES or key in {"vcsnnetworknumber", "network"}:
        metadata.setdefault("station", value)
    elif key in LAT_ALIASES:
        metadata.setdefault("latitude", value)
    elif key in LON_ALIASES:
        metadata.setdefault("longitude", value)
    elif key in NAME_ALIASES:
        metadata.setdefault("place_name", value)
    elif key in REGION_ALIASES:
        metadata.setdefault("region", value)


def looks_like_header(line: str) -> bool:
    try:
        fields = next(csv.reader([line]))
    except csv.Error:
        return False
    names = {normalise(field) for field in fields}
    return bool(names & DATE_ALIASES) and bool(names & (WIND_ALIASES | RADIATION_ALIASES))


def iter_paths(inputs: list[Path]) -> Iterable[Path]:
    for path in inputs:
        if path.is_dir():
            for pattern in ("*.csv", "*.txt", "*.csv.gz", "*.zip"):
                yield from sorted(path.rglob(pattern))
        elif path.exists():
            yield path


def iter_csv_sources(inputs: list[Path]) -> Iterable[tuple[str, TextIO]]:
    for path in iter_paths(inputs):
        suffixes = [suffix.lower() for suffix in path.suffixes]
        if suffixes[-2:] == [".csv", ".gz"] or path.suffix.lower() == ".gz":
            with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
                yield str(path), handle
        elif path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if not name.lower().endswith((".csv", ".txt")):
                        continue
                    with archive.open(name) as raw:
                        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                        yield f"{path}!{name}", text
        elif path.suffix.lower() in {".csv", ".txt"}:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                yield str(path), handle


def dict_rows_from_source(handle: TextIO) -> tuple[dict[str, str], csv.DictReader] | None:
    metadata: dict[str, str] = {}
    while True:
        line = handle.readline()
        if line == "":
            return None
        if looks_like_header(line):
            return metadata, csv.DictReader(_line_chain(line, handle))
        parse_metadata_line(line, metadata)


def _line_chain(first_line: str, handle: TextIO) -> Iterable[str]:
    yield first_line
    yield from handle


def load_station_metadata(path: Path | None) -> dict[str, StationMeta]:
    if not path or not path.exists():
        return {}
    metadata: dict[str, StationMeta] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        station_col = first_column(reader.fieldnames or [], STATION_ALIASES)
        lat_col = first_column(reader.fieldnames or [], LAT_ALIASES)
        lon_col = first_column(reader.fieldnames or [], LON_ALIASES)
        region_col = first_column(reader.fieldnames or [], REGION_ALIASES)
        name_col = first_column(reader.fieldnames or [], NAME_ALIASES)
        for row in reader:
            station_id = value_for(row, station_col)
            if not station_id:
                continue
            place_name = value_for(row, name_col) or f"VCSN {station_id}"
            metadata[station_id] = StationMeta(
                station_id=station_id,
                place_name=place_name,
                latitude=safe_float(value_for(row, lat_col)),
                longitude=safe_float(value_for(row, lon_col)),
                region=value_for(row, region_col) or "",
            )
    return metadata


def metadata_from_header(header_metadata: dict[str, str], source_name: str) -> StationMeta:
    station_id = header_metadata.get("station") or Path(source_name.split("!")[0]).stem
    return StationMeta(
        station_id=station_id,
        place_name=header_metadata.get("place_name") or f"VCSN {station_id}",
        latitude=safe_float(header_metadata.get("latitude")),
        longitude=safe_float(header_metadata.get("longitude")),
        region=header_metadata.get("region", ""),
    )


def update_aggregate(
    aggregates: dict[str, StationAggregate],
    row: dict[str, str],
    fieldnames: list[str],
    station_metadata: dict[str, StationMeta],
    header_meta: StationMeta,
) -> None:
    station_col = first_column(fieldnames, STATION_ALIASES)
    date_col = first_column(fieldnames, DATE_ALIASES)
    lat_col = first_column(fieldnames, LAT_ALIASES)
    lon_col = first_column(fieldnames, LON_ALIASES)
    region_col = first_column(fieldnames, REGION_ALIASES)
    name_col = first_column(fieldnames, NAME_ALIASES)
    wind_col = first_column(fieldnames, WIND_ALIASES)
    radiation_col = first_column(fieldnames, RADIATION_ALIASES)

    station_id = value_for(row, station_col) or header_meta.station_id
    if not station_id:
        return
    meta = station_metadata.get(station_id)
    if meta is None:
        if header_meta.station_id == station_id:
            meta = header_meta
        else:
            meta = StationMeta(station_id=station_id, place_name=f"VCSN {station_id}")
    place_name = value_for(row, name_col) or meta.place_name or f"VCSN {station_id}"
    latitude = safe_float(value_for(row, lat_col)) if lat_col else meta.latitude
    longitude = safe_float(value_for(row, lon_col)) if lon_col else meta.longitude
    region = value_for(row, region_col) or meta.region

    if latitude is None or longitude is None:
        return

    aggregate = aggregates.setdefault(
        station_id,
        StationAggregate(
            station_id=station_id,
            place_name=place_name,
            region=region,
            latitude=latitude,
            longitude=longitude,
        ),
    )
    aggregate.place_name = place_name
    aggregate.region = region
    aggregate.latitude = latitude
    aggregate.longitude = longitude

    parsed_date = safe_date(value_for(row, date_col))
    if parsed_date:
        aggregate.dates.append(parsed_date)

    wind = safe_float(value_for(row, wind_col))
    radiation = safe_float(value_for(row, radiation_col))
    if wind is not None:
        aggregate.wind10_values.append(wind)
    if radiation is not None:
        aggregate.radiation_mj_values.append(radiation)


def read_vcsn_inputs(inputs: list[Path], station_metadata_path: Path | None) -> dict[str, StationAggregate]:
    station_metadata = load_station_metadata(station_metadata_path)
    aggregates: dict[str, StationAggregate] = {}
    source_count = 0

    for source_name, handle in iter_csv_sources(inputs):
        result = dict_rows_from_source(handle)
        if result is None:
            continue
        header_metadata, reader = result
        header_meta = metadata_from_header(header_metadata, source_name)
        fieldnames = reader.fieldnames or []
        source_count += 1
        log(f"[read] {source_name}")
        for row in reader:
            update_aggregate(aggregates, row, fieldnames, station_metadata, header_meta)

    log(f"[input] read {source_count} CSV source(s)")
    return aggregates


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * pct)
    return ordered[index]


def summaries_from_aggregates(aggregates: dict[str, StationAggregate], wind_shear_alpha: float) -> list[dict]:
    summaries: list[dict] = []
    height_factor = (100.0 / 10.0) ** wind_shear_alpha

    for aggregate in aggregates.values():
        if aggregate.latitude is None or aggregate.longitude is None:
            continue
        dates = sorted(set(aggregate.dates))
        wind100 = [value * height_factor for value in aggregate.wind10_values]
        total_radiation_mj = sum(aggregate.radiation_mj_values)
        total_radiation_kwh = total_radiation_mj / 3.6
        daily_count = max(len(dates), len(aggregate.wind10_values), len(aggregate.radiation_mj_values), 1)
        daily_avg_solar_kwh = total_radiation_kwh / daily_count
        mean_radiation_wm2 = mean([value * 1_000_000.0 / 86_400.0 for value in aggregate.radiation_mj_values])
        mean_wind100 = mean(wind100)

        summaries.append(
            {
                "place_name": aggregate.place_name,
                "region": aggregate.region,
                "latitude": round(aggregate.latitude, 6),
                "longitude": round(aggregate.longitude, 6),
                "start_date": dates[0] if dates else "",
                "end_date": dates[-1] if dates else "",
                "hour_count": daily_count,
                "mean_wind_speed_10m_ms": round(mean(aggregate.wind10_values) or 0.0, 3),
                "mean_wind_speed_100m_ms": round(mean_wind100 or 0.0, 3),
                "p90_wind_speed_100m_ms": round(percentile(wind100, 0.9) or 0.0, 3),
                "max_wind_gust_10m_ms": None,
                "mean_shortwave_radiation_wm2": round(mean_radiation_wm2 or 0.0, 3),
                "total_shortwave_radiation_kwh_m2": round(total_radiation_kwh, 3),
                "total_sunshine_hours": None,
                "wind_resource_score": round(min(100.0, max(0.0, ((mean_wind100 or 0.0) / 9.0) * 100.0)), 1),
                "solar_resource_score": round(min(100.0, max(0.0, (daily_avg_solar_kwh / 6.0) * 100.0)), 1),
                "data_source": "NIWA / Earth Sciences NZ VCSN daily data",
                "vcsn_station": aggregate.station_id,
            }
        )

    return sorted(summaries, key=lambda item: item["place_name"])


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
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
                "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
            }
        )
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "vcsn_weather_resource_summary",
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
            data_source TEXT NOT NULL DEFAULT 'Unknown',
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
            data_source,
            geom
        )
        VALUES (
            %(place_name)s,
            %(region)s,
            %(latitude)s,
            %(longitude)s,
            NULLIF(%(start_date)s, '')::date,
            NULLIF(%(end_date)s, '')::date,
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
            data_source = EXCLUDED.data_source,
            geom = EXCLUDED.geom;
    """

    inserted = 0
    with psycopg2.connect(db_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(create_sql)
            for summary in summaries:
                if not summary["start_date"] or not summary["end_date"]:
                    continue
                cursor.execute(insert_sql, summary)
                inserted += cursor.rowcount
    return inserted


def require_requests() -> None:
    if requests is None:
        raise RuntimeError("DataHub download requires requests. Install with: py -m pip install requests")


def datahub_headers(accept: str) -> dict[str, str]:
    require_requests()
    customer_id = os.getenv("NIWA_CUSTOMER_ID")
    api_key = os.getenv("NIWA_API_KEY")
    if not customer_id or not api_key:
        raise RuntimeError("Set NIWA_CUSTOMER_ID and NIWA_API_KEY before using DataHub download options.")
    return {
        "X-Customer-ID": customer_id,
        "Authorization": f"Bearer {api_key}",
        "Accept": accept,
    }


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "datahub_file"


def extension_from_response(content_type: str, file_name: str) -> str:
    suffix = Path(file_name).suffix
    if suffix:
        return suffix
    content_type = content_type.lower()
    if "zip" in content_type:
        return ".zip"
    if "gzip" in content_type:
        return ".csv.gz"
    return ".csv"


def save_datahub_url(download_url: str, output_dir: Path, timeout: int, file_name: str) -> Path:
    file_response = requests.get(download_url, timeout=timeout)
    file_response.raise_for_status()
    extension = extension_from_response(file_response.headers.get("content-type", ""), file_name)
    output_path = output_dir / safe_filename(file_name)
    if not output_path.suffix:
        output_path = output_path.with_suffix(extension)
    output_path.write_bytes(file_response.content)
    return output_path


def download_datahub_file(file_id: str, output_dir: Path, timeout: int) -> Path:
    require_requests()

    output_dir.mkdir(parents=True, exist_ok=True)
    headers = datahub_headers("application/json")
    response = requests.get(DATAHUB_FILE_API.format(file_id=file_id), headers=headers, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    download_url = payload.get("presignedUrl") or payload.get("url")
    if not download_url.startswith("http"):
        raise RuntimeError("DataHub did not return a direct download URL.")
    file_name = payload.get("fileName") or file_id
    return save_datahub_url(download_url, output_dir, timeout, file_name)


def list_datahub_files(timeout: int, limit: int) -> list[dict]:
    require_requests()
    headers = datahub_headers("application/json")
    files: list[dict] = []
    page = 1

    while True:
        response = requests.get(
            DATAHUB_FILES_API,
            headers=headers,
            params={"page": page, "limit": limit, "includeMetadata": "true"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        files.extend(payload.get("data", []))

        pagination = payload.get("pagination") or {}
        total_pages = int(pagination.get("totalPages") or page)
        if page >= total_pages:
            break
        page += 1

    return files


def datahub_file_matches(file_info: dict, filters: list[str]) -> bool:
    if not filters:
        return True
    haystack = json.dumps(file_info, ensure_ascii=False).lower()
    return all(item.lower() in haystack for item in filters)


def download_matching_datahub_files(
    output_dir: Path,
    timeout: int,
    limit: int,
    name_filters: list[str],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = list_datahub_files(timeout=timeout, limit=limit)
    matched = [file_info for file_info in files if datahub_file_matches(file_info, name_filters)]
    log(f"[datahub] listed {len(files)} file(s), matched {len(matched)} file(s)")

    downloaded: list[Path] = []
    for index, file_info in enumerate(matched, start=1):
        file_id = file_info.get("id") or file_info.get("_id")
        if not file_id:
            continue
        file_name = file_info.get("fileName") or file_id
        log(f"[datahub] downloading {index}/{len(matched)} {file_name}")
        downloaded.append(download_datahub_file(file_id, output_dir, timeout))
    return downloaded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import NIWA / Earth Sciences NZ VCSN wind and solar resource data.")
    parser.add_argument("--input", type=Path, nargs="*", default=[DEFAULT_INPUT], help="CSV, CSV.GZ, ZIP, or folder.")
    parser.add_argument("--station-metadata", type=Path, default=None, help="Optional station coordinate metadata CSV.")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--geojson-output", type=Path, default=DEFAULT_SUMMARY_GEOJSON)
    parser.add_argument("--wind-shear-alpha", type=float, default=0.143, help="Power-law exponent for 10 m to 100 m wind estimate.")
    parser.add_argument("--insert-db", action="store_true")
    parser.add_argument("--db-dsn", default=default_db_dsn())
    parser.add_argument("--db-schema", default=os.getenv("POSTGIS_SCHEMA", "renewable_nz"))
    parser.add_argument("--datahub-file-id", default=None, help="Optional NIWA DataHub file id to download before import.")
    parser.add_argument("--download-all-datahub-files", action="store_true", help="Download every matching file from your DataHub orders.")
    parser.add_argument(
        "--datahub-name-contains",
        action="append",
        default=[],
        help="Filter DataHub files by text found in filename or metadata. Can be repeated.",
    )
    parser.add_argument("--datahub-page-limit", type=int, default=100, help="Files to request per DataHub API page.")
    parser.add_argument("--download-only", action="store_true", help="Download DataHub files without importing them.")
    parser.add_argument("--download-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inputs = args.input
    log("[start] VCSN weather resource pipeline")

    if args.datahub_file_id:
        downloaded = download_datahub_file(args.datahub_file_id, args.download_dir, args.timeout)
        log(f"[download] {downloaded}")
        inputs = [downloaded]
    elif args.download_all_datahub_files:
        downloaded_files = download_matching_datahub_files(
            output_dir=args.download_dir,
            timeout=args.timeout,
            limit=args.datahub_page_limit,
            name_filters=args.datahub_name_contains,
        )
        if not downloaded_files:
            log("[result] No DataHub files were downloaded.")
            return 1
        inputs = downloaded_files

    if args.download_only:
        log("[done] DataHub download completed; import skipped because --download-only was set.")
        return 0

    aggregates = read_vcsn_inputs(inputs, args.station_metadata)
    summaries = summaries_from_aggregates(aggregates, args.wind_shear_alpha)
    if not summaries:
        log("[result] No VCSN summaries were generated. Check input CSV fields and station coordinates.")
        return 1

    write_csv(args.summary_output, summaries)
    write_geojson(args.geojson_output, summaries)
    log(f"[output] summary CSV: {args.summary_output}")
    log(f"[output] summary GeoJSON: {args.geojson_output}")
    log(f"[result] generated {len(summaries)} VCSN point summaries")

    if args.insert_db:
        inserted = insert_summaries_to_postgis(summaries, args.db_dsn, args.db_schema)
        log(f"[db] upserted {inserted} rows into {args.db_schema}.weather_resource_summary")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
