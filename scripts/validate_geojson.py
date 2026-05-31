"""Validate GeoJSON files used by the WebGIS frontend."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def iter_positions(geometry: dict[str, Any]):
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")

    if geom_type == "Point":
        yield coords
    elif geom_type in {"LineString", "MultiPoint"}:
        yield from coords
    elif geom_type in {"Polygon", "MultiLineString"}:
        for part in coords:
            yield from part
    elif geom_type == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield from ring
    else:
        raise ValueError(f"Unsupported geometry type: {geom_type}")


def validate_position(position: list[float], feature_index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(position, list) or len(position) < 2:
        return [f"Feature {feature_index}: invalid coordinate {position!r}"]

    lon, lat = position[:2]
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in [lon, lat]):
        errors.append(f"Feature {feature_index}: coordinate is not finite")
    if not -180 <= lon <= 180:
        errors.append(f"Feature {feature_index}: longitude out of range {lon}")
    if not -90 <= lat <= 90:
        errors.append(f"Feature {feature_index}: latitude out of range {lat}")
    return errors


def validate_geojson(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))

    if data.get("type") != "FeatureCollection":
        errors.append("Root object must be a FeatureCollection")
        return errors

    features = data.get("features")
    if not isinstance(features, list):
        errors.append("features must be a list")
        return errors

    for index, feature in enumerate(features, start=1):
        if feature.get("type") != "Feature":
            errors.append(f"Feature {index}: type must be Feature")
            continue
        if not isinstance(feature.get("properties"), dict):
            errors.append(f"Feature {index}: properties must be an object")
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            errors.append(f"Feature {index}: geometry must be an object")
            continue
        try:
            for position in iter_positions(geometry):
                errors.extend(validate_position(position, index))
        except ValueError as exc:
            errors.append(f"Feature {index}: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a GeoJSON FeatureCollection.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    had_errors = False
    for path in args.paths:
        errors = validate_geojson(path)
        if errors:
            had_errors = True
            print(f"{path}: FAILED")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"{path}: OK")

    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
