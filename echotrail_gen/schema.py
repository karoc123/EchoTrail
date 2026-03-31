"""Schema / data-loading layer.

Reads the on-disk content structure and returns plain Python objects
(dicts) that the builder passes into Jinja2 templates.

Directory layout expected::

    data/
      trips/
        <trip_id>/
          title.txt
          description.md
          odometer_km.txt
          route.geojson        (preferred)
          route.gpx            (converted if no .geojson present)
          cover.jpg            (optional)
          entries/
            <entry_id>/
              point.geojson
              date.txt
              text.md
              country.txt      (optional)
              weather.txt      (optional)
              temperature_c.txt (optional)
              media/
                *.jpg / *.png / *.mp4 …
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from echotrail_gen.geo import gpx_to_geojson, load_geojson

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RESERVED_FILES = {
    "title.txt",
    "description.md",
    "odometer_km.txt",
    "route.geojson",
    "route.gpx",
    "cover.jpg",
    "cover.jpeg",
    "cover.png",
    "meta.json",
}

_ENTRY_RESERVED_FILES = {
    "point.geojson",
    "date.txt",
    "text.md",
    "country.txt",
    "weather.txt",
    "temperature_c.txt",
    "meta.json",
}

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov"}


def _read_text(path: Path) -> str:
    """Return stripped text content of *path*, or empty string if missing."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _extra_metadata(directory: Path, reserved: set[str]) -> dict[str, str]:
    """Return a dict of all *.txt files not in *reserved*, keyed by stem."""
    meta: dict[str, str] = {}
    for p in sorted(directory.glob("*.txt")):
        if p.name not in reserved:
            meta[p.stem] = _read_text(p)
    return meta


def _media_files(media_dir: Path) -> list[dict[str, str]]:
    """Return sorted list of media file descriptors from *media_dir*."""
    if not media_dir.is_dir():
        return []
    files: list[dict[str, str]] = []
    for p in sorted(media_dir.iterdir()):
        ext = p.suffix.lower()
        if ext in _IMAGE_EXTS:
            files.append({"type": "image", "name": p.name})
        elif ext in _VIDEO_EXTS:
            files.append({"type": "video", "name": p.name})
    return files


# ---------------------------------------------------------------------------
# Entry loader
# ---------------------------------------------------------------------------


def load_entry(entry_dir: Path, trip_id: str) -> dict[str, Any]:
    """Load one entry directory and return a descriptor dict."""
    entry_id = entry_dir.name

    # Point geometry
    point_geojson_path = entry_dir / "point.geojson"
    point_geojson: dict[str, Any] | None = None
    if point_geojson_path.exists():
        try:
            point_geojson = load_geojson(point_geojson_path)
        except Exception as exc:
            log.warning("Could not load %s: %s", point_geojson_path, exc)

    # Core fields
    date = _read_text(entry_dir / "date.txt")
    text_md = _read_text(entry_dir / "text.md")
    country = _read_text(entry_dir / "country.txt")
    weather = _read_text(entry_dir / "weather.txt")
    temperature_c = _read_text(entry_dir / "temperature_c.txt")

    # Optional meta.json (future-proofing)
    meta_json: dict[str, Any] = {}
    meta_path = entry_dir / "meta.json"
    if meta_path.exists():
        try:
            meta_json = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not parse %s: %s", meta_path, exc)

    # Extra *.txt files
    extra = _extra_metadata(entry_dir, _ENTRY_RESERVED_FILES)

    # Media
    media = _media_files(entry_dir / "media")

    return {
        "id": entry_id,
        "trip_id": trip_id,
        "url": f"trips/{trip_id}/entries/{entry_id}/",
        "date": date,
        "text_md": text_md,
        "country": country,
        "weather": weather,
        "temperature_c": temperature_c,
        "point_geojson": point_geojson,
        "point_geojson_json": json.dumps(point_geojson) if point_geojson else "null",
        "media": media,
        "extra": extra,
        "meta": meta_json,
    }


# ---------------------------------------------------------------------------
# Trip loader
# ---------------------------------------------------------------------------


def load_trip(trip_dir: Path) -> dict[str, Any]:
    """Load one trip directory and return a descriptor dict."""
    trip_id = trip_dir.name

    # Title / description
    title = _read_text(trip_dir / "title.txt") or trip_id
    description_md = _read_text(trip_dir / "description.md")
    odometer_km = _read_text(trip_dir / "odometer_km.txt")

    # Cover image (optional)
    cover: str | None = None
    for cname in ("cover.jpg", "cover.jpeg", "cover.png"):
        if (trip_dir / cname).exists():
            cover = cname
            break

    # Route geometry — prefer GeoJSON, fall back to GPX conversion
    route_geojson: dict[str, Any] | None = None
    geojson_path = trip_dir / "route.geojson"
    gpx_path = trip_dir / "route.gpx"
    if geojson_path.exists():
        try:
            route_geojson = load_geojson(geojson_path)
        except Exception as exc:
            log.warning("Could not load %s: %s", geojson_path, exc)
    elif gpx_path.exists():
        log.info("Converting %s to GeoJSON …", gpx_path)
        try:
            route_geojson = gpx_to_geojson(gpx_path)
        except Exception as exc:
            log.warning("Could not convert %s: %s", gpx_path, exc)

    # Optional meta.json
    meta_json: dict[str, Any] = {}
    meta_path = trip_dir / "meta.json"
    if meta_path.exists():
        try:
            meta_json = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not parse %s: %s", meta_path, exc)

    # Extra *.txt files
    extra = _extra_metadata(trip_dir, _RESERVED_FILES)

    # Entries
    entries_dir = trip_dir / "entries"
    entries: list[dict[str, Any]] = []
    if entries_dir.is_dir():
        for entry_dir in sorted(entries_dir.iterdir()):
            if entry_dir.is_dir():
                entries.append(load_entry(entry_dir, trip_id))

    return {
        "id": trip_id,
        "url": f"trips/{trip_id}/",
        "title": title,
        "description_md": description_md,
        "odometer_km": odometer_km,
        "cover": cover,
        "route_geojson": route_geojson,
        "route_geojson_json": json.dumps(route_geojson) if route_geojson else "null",
        "entries": entries,
        "extra": extra,
        "meta": meta_json,
    }


# ---------------------------------------------------------------------------
# Top-level loader
# ---------------------------------------------------------------------------


def load_all_trips(data_dir: Path) -> list[dict[str, Any]]:
    """Load every trip found under *data_dir/trips/* and return a list."""
    trips_root = data_dir / "trips"
    if not trips_root.is_dir():
        log.warning("No trips directory found at %s", trips_root)
        return []

    trips: list[dict[str, Any]] = []
    for trip_dir in sorted(trips_root.iterdir()):
        if trip_dir.is_dir():
            log.info("Loading trip: %s", trip_dir.name)
            trips.append(load_trip(trip_dir))
    return trips
