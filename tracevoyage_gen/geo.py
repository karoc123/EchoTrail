"""Geo helpers: GeoJSON loading and GPX → GeoJSON conversion."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from tracevoyage_gen.exceptions import GeoProcessingError


def load_geojson(path: Path) -> dict[str, Any]:
    """Load and return a GeoJSON file as a dict."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}, got {type(data).__name__}")
    return data


def gpx_to_geojson(path: Path) -> dict[str, Any]:
    """Convert a GPX file to a GeoJSON FeatureCollection.

    Extracts:
    - ``<trk>/<trkseg>/<trkpt>`` track points → LineString feature
    - ``<wpt>`` waypoints → Point features

    Raises:
        GeoProcessingError: If the GPX file is malformed or contains invalid data
    """
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        raise GeoProcessingError(path, f"Invalid GPX XML: {e}") from e

    root = tree.getroot()

    # GPX namespace may or may not be present
    ns_prefix = ""
    if root.tag.startswith("{"):
        ns_prefix = root.tag.split("}")[0] + "}"

    def tag(name: str) -> str:
        return f"{ns_prefix}{name}"

    features: list[dict[str, Any]] = []

    # --- Track segments → LineString ---
    for trk in root.iter(tag("trk")):
        trk_name_el = trk.find(tag("name"))
        trk_name = trk_name_el.text.strip() if trk_name_el is not None and trk_name_el.text else None
        coords: list[list[float]] = []
        for trkpt in trk.iter(tag("trkpt")):
            try:
                lat = float(trkpt.attrib["lat"])
                lon = float(trkpt.attrib["lon"])
            except (KeyError, ValueError) as e:
                raise GeoProcessingError(path, f"Invalid track point: {e}") from e

            # Validate coordinate ranges
            if not (-90 <= lat <= 90):
                raise GeoProcessingError(path, f"Invalid latitude {lat}: must be between -90 and 90")
            if not (-180 <= lon <= 180):
                raise GeoProcessingError(path, f"Invalid longitude {lon}: must be between -180 and 180")

            ele_el = trkpt.find(tag("ele"))
            if ele_el is not None and ele_el.text:
                coords.append([lon, lat, float(ele_el.text)])
            else:
                coords.append([lon, lat])
        if coords:
            props: dict[str, Any] = {}
            if trk_name:
                props["name"] = trk_name
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": props,
                }
            )

    # --- Waypoints → Point ---
    for wpt in root.iter(tag("wpt")):
        try:
            lat = float(wpt.attrib["lat"])
            lon = float(wpt.attrib["lon"])
        except (KeyError, ValueError) as e:
            raise GeoProcessingError(path, f"Invalid waypoint: {e}") from e

        # Validate coordinate ranges
        if not (-90 <= lat <= 90):
            raise GeoProcessingError(path, f"Invalid waypoint latitude {lat}: must be between -90 and 90")
        if not (-180 <= lon <= 180):
            raise GeoProcessingError(path, f"Invalid waypoint longitude {lon}: must be between -180 and 180")

        ele_el = wpt.find(tag("ele"))
        name_el = wpt.find(tag("name"))
        desc_el = wpt.find(tag("desc"))
        ele = float(ele_el.text) if ele_el is not None and ele_el.text else None
        props = {}
        if name_el is not None and name_el.text:
            props["name"] = name_el.text.strip()
        if desc_el is not None and desc_el.text:
            props["description"] = desc_el.text.strip()
        coord: list[float] = [lon, lat] if ele is None else [lon, lat, ele]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coord},
                "properties": props,
            }
        )

    return {"type": "FeatureCollection", "features": features}
