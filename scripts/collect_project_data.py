"""Run both project data collection pipelines.

The project uses two separate collection methods:
1. Web text GIR: scrape article/page text, extract place names, and create GIR points.
2. Weather resource history: download structured wind and solar variables for analysis points.

This wrapper keeps those methods separate while making VM runs easier.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GIR_SCRIPT = PROJECT_ROOT / "scripts" / "gir_pipeline.py"
WEATHER_SCRIPT = PROJECT_ROOT / "scripts" / "weather_history_pipeline.py"


def log(message: str) -> None:
    print(message, flush=True)


def run_command(command: list[str]) -> None:
    log(f"[run] {' '.join(command)}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def add_common_db_args(command: list[str], args: argparse.Namespace) -> list[str]:
    if args.insert_db:
        command.append("--insert-db")
        command.extend(["--db-dsn", args.db_dsn])
        command.extend(["--db-schema", args.db_schema])
    return command


def build_gir_command(args: argparse.Namespace) -> list[str]:
    command = [sys.executable, str(GIR_SCRIPT)]

    if args.gir_offline_sample:
        command.append("--offline-sample")
    if args.gir_auto_discover:
        command.append("--auto-discover")
    if args.gir_deep_scan:
        command.append("--deep-scan")
    if args.gir_offline_geocode:
        command.append("--offline-geocode")
    if args.include_facebook_csv:
        command.append("--include-facebook-csv")

    command.extend(["--max-pages-per-site", str(args.gir_max_pages_per_site)])
    if args.gir_sites:
        command.append("--sites")
        command.extend(args.gir_sites)
    if args.gir_keywords:
        command.extend(["--keywords", args.gir_keywords])
    if args.gir_frontend_output:
        command.extend(["--frontend-output", str(args.gir_frontend_output)])

    return add_common_db_args(command, args)


def build_weather_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(WEATHER_SCRIPT),
        "--start-date",
        args.weather_start_date,
        "--end-date",
        args.weather_end_date,
        "--locations",
        str(args.weather_locations),
    ]
    return add_common_db_args(command, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GIR and weather resource data collection.")
    parser.add_argument("--skip-gir", action="store_true", help="Do not run the web text GIR pipeline.")
    parser.add_argument("--skip-weather", action="store_true", help="Do not run the weather history pipeline.")

    parser.add_argument("--insert-db", action="store_true", help="Insert outputs into PostGIS.")
    parser.add_argument(
        "--db-dsn",
        default="host=localhost port=5432 dbname=renewable_nz user=postgres",
        help="PostGIS connection string.",
    )
    parser.add_argument("--db-schema", default="renewable_nz")

    parser.add_argument("--gir-auto-discover", action="store_true", help="Discover GIR pages from public sitemaps.")
    parser.add_argument("--gir-offline-sample", action="store_true", help="Use local sample GIR articles.")
    parser.add_argument("--gir-deep-scan", action="store_true", help="Scan more sitemap URLs for GIR.")
    parser.add_argument("--gir-offline-geocode", action="store_true", help="Use local place coordinates for GIR geocoding.")
    parser.add_argument("--include-facebook-csv", action="store_true", help="Include manually exported Facebook CSV text.")
    parser.add_argument("--gir-max-pages-per-site", type=int, default=80)
    parser.add_argument("--gir-sites", nargs="*", default=None)
    parser.add_argument("--gir-keywords", default=None)
    parser.add_argument(
        "--gir-frontend-output",
        type=Path,
        default=PROJECT_ROOT / "frontend" / "data" / "gir_mentions.geojson",
    )

    parser.add_argument("--weather-start-date", default="2024-01-01")
    parser.add_argument("--weather-end-date", default="2024-12-31")
    parser.add_argument(
        "--weather-locations",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "weather_locations_extended.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_gir and args.skip_weather:
        raise SystemExit("Nothing to run: both --skip-gir and --skip-weather were set.")

    log("[start] Project data collection")
    log("[method] GIR web text and weather history are collected as separate datasets")

    if not args.skip_gir:
        if not args.gir_auto_discover and not args.gir_offline_sample and not args.include_facebook_csv:
            log("[gir] no GIR input mode was selected; using --gir-auto-discover")
            args.gir_auto_discover = True
        run_command(build_gir_command(args))

    if not args.skip_weather:
        run_command(build_weather_command(args))

    log("[done] Data collection completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
