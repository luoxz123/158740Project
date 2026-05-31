"""Configure GeoServer workspace, PostGIS layers, and SLD styles."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STYLES_DIR = PROJECT_ROOT / "geoserver" / "styles"

LAYERS = [
    ("wind_suitability", "wind_style"),
    ("solar_suitability", "solar_style"),
    ("transmission_lines", "transmission_style"),
    ("roads", "roads_style"),
    ("protected_areas", "protected_areas_style"),
    ("gir_locations", "gir_locations_style"),
    ("weather_resource_summary", "weather_resource_style"),
    ("site_selection_candidates", "site_selection_style"),
]


def log(message: str) -> None:
    print(message, flush=True)


class GeoServerClient:
    def __init__(self, base_url: str, user: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = (user, password)

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        data: str | bytes | None = None,
        content_type: str | None = None,
        ok_statuses: tuple[int, ...] = (200, 201),
    ) -> requests.Response:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        response = requests.request(
            method,
            self.url(path),
            auth=self.auth,
            json=json_payload,
            data=data,
            headers=headers,
            timeout=30,
        )
        if response.status_code not in ok_statuses:
            raise RuntimeError(
                f"GeoServer {method} {path} failed with {response.status_code}: {response.text[:500]}"
            )
        return response

    def exists(self, path: str) -> bool:
        response = requests.get(self.url(path), auth=self.auth, timeout=20)
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        raise RuntimeError(f"GeoServer GET {path} failed with {response.status_code}: {response.text[:500]}")


def wait_for_geoserver(client: GeoServerClient, attempts: int, delay: float) -> None:
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(client.url("/rest/about/version.json"), auth=client.auth, timeout=10)
            if response.status_code == 200:
                log("[geoserver] REST API is ready")
                return
            log(f"[geoserver] waiting ({attempt}/{attempts}): HTTP {response.status_code}")
        except requests.RequestException as exc:
            log(f"[geoserver] waiting ({attempt}/{attempts}): {exc}")
        time.sleep(delay)
    raise RuntimeError("GeoServer REST API did not become ready in time.")


def ensure_workspace(client: GeoServerClient, workspace: str) -> None:
    if client.exists(f"/rest/workspaces/{workspace}.json"):
        log(f"[geoserver] workspace exists: {workspace}")
        return
    client.request(
        "POST",
        "/rest/workspaces",
        json_payload={"workspace": {"name": workspace}},
    )
    log(f"[geoserver] created workspace: {workspace}")


def ensure_datastore(client: GeoServerClient, args: argparse.Namespace) -> None:
    path = f"/rest/workspaces/{args.workspace}/datastores/{args.store}.json"
    payload = {
        "dataStore": {
            "name": args.store,
            "connectionParameters": {
                "entry": [
                    {"@key": "dbtype", "$": "postgis"},
                    {"@key": "host", "$": args.postgis_host},
                    {"@key": "port", "$": str(args.postgis_port)},
                    {"@key": "database", "$": args.postgis_db},
                    {"@key": "schema", "$": args.postgis_schema},
                    {"@key": "user", "$": args.postgis_user},
                    {"@key": "passwd", "$": args.postgis_password},
                    {"@key": "Expose primary keys", "$": "true"},
                    {"@key": "Loose bbox", "$": "true"},
                ]
            },
        }
    }

    if client.exists(path):
        client.request("PUT", path, json_payload=payload, ok_statuses=(200,))
        log(f"[geoserver] updated datastore: {args.store}")
        return

    client.request(
        "POST",
        f"/rest/workspaces/{args.workspace}/datastores",
        json_payload=payload,
    )
    log(f"[geoserver] created datastore: {args.store}")


def ensure_style(client: GeoServerClient, workspace: str, styles_dir: Path, style_name: str) -> None:
    sld_path = styles_dir / f"{style_name}.sld"
    if not sld_path.exists():
        log(f"[skip] missing style file: {sld_path}")
        return

    style_path = f"/rest/workspaces/{workspace}/styles/{style_name}.json"
    if not client.exists(style_path):
        client.request(
            "POST",
            f"/rest/workspaces/{workspace}/styles",
            json_payload={"style": {"name": style_name, "filename": sld_path.name}},
        )
        log(f"[geoserver] created style record: {style_name}")

    client.request(
        "PUT",
        f"/rest/workspaces/{workspace}/styles/{style_name}",
        data=sld_path.read_bytes(),
        content_type="application/vnd.ogc.sld+xml",
        ok_statuses=(200,),
    )
    log(f"[geoserver] uploaded style: {style_name}")


def ensure_layer(client: GeoServerClient, workspace: str, store: str, layer_name: str, style_name: str) -> None:
    feature_type_path = f"/rest/workspaces/{workspace}/datastores/{store}/featuretypes/{layer_name}.json"
    if not client.exists(feature_type_path):
        client.request(
            "POST",
            f"/rest/workspaces/{workspace}/datastores/{store}/featuretypes",
            json_payload={
                "featureType": {
                    "name": layer_name,
                    "nativeName": layer_name,
                    "title": layer_name.replace("_", " ").title(),
                    "srs": "EPSG:2193",
                    "projectionPolicy": "FORCE_DECLARED",
                }
            },
        )
        log(f"[geoserver] published layer: {workspace}:{layer_name}")
    else:
        log(f"[geoserver] layer exists: {workspace}:{layer_name}")

    client.request(
        "PUT",
        f"/rest/layers/{workspace}:{layer_name}",
        json_payload={"layer": {"defaultStyle": {"name": style_name, "workspace": workspace}}},
        ok_statuses=(200,),
    )
    log(f"[geoserver] assigned style {style_name} to {layer_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure GeoServer for the renewable_nz project.")
    parser.add_argument("--geoserver-url", default=os.getenv("GEOSERVER_URL", "http://localhost:8080/geoserver"))
    parser.add_argument("--geoserver-user", default=os.getenv("GEOSERVER_USER", "admin"))
    parser.add_argument("--geoserver-password", default=os.getenv("GEOSERVER_PASSWORD", "geoserver"))
    parser.add_argument("--workspace", default=os.getenv("GEOSERVER_WORKSPACE", "renewable_nz"))
    parser.add_argument("--store", default=os.getenv("GEOSERVER_STORE", "postgis_renewable_nz"))
    parser.add_argument("--postgis-host", default=os.getenv("POSTGIS_HOST", "localhost"))
    parser.add_argument("--postgis-port", default=os.getenv("POSTGIS_PORT", "5432"))
    parser.add_argument("--postgis-db", default=os.getenv("POSTGIS_DB", "renewable_nz"))
    parser.add_argument("--postgis-schema", default=os.getenv("POSTGIS_SCHEMA", "renewable_nz"))
    parser.add_argument("--postgis-user", default=os.getenv("POSTGIS_USER", "postgres"))
    parser.add_argument("--postgis-password", default=os.getenv("POSTGIS_PASSWORD", "Postgres123"))
    parser.add_argument("--styles-dir", type=Path, default=DEFAULT_STYLES_DIR)
    parser.add_argument("--wait-attempts", type=int, default=60)
    parser.add_argument("--wait-delay", type=float, default=3.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = GeoServerClient(args.geoserver_url, args.geoserver_user, args.geoserver_password)

    wait_for_geoserver(client, args.wait_attempts, args.wait_delay)
    ensure_workspace(client, args.workspace)
    ensure_datastore(client, args)

    for _, style_name in LAYERS:
        ensure_style(client, args.workspace, args.styles_dir, style_name)

    for layer_name, style_name in LAYERS:
        ensure_layer(client, args.workspace, args.store, layer_name, style_name)

    log("[done] GeoServer configuration complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
