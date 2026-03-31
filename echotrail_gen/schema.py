"""Schema / data-loading layer.

Reads the on-disk content structure and returns plain Python objects
(dicts) that the builder passes into Jinja2 templates.

Metadata is stored as TOML front matter (Hugo-style ``+++`` delimiters)
inside the Markdown files.

Directory layout expected::

    data/
      trips/
        <trip_id>/
          description.md       (with +++ front matter: title, odometer_km, …)
          route.geojson        (preferred)
          route.gpx            (converted if no .geojson present)
          cover.jpg            (optional)
          entries/
            <entry_id>/
              text.md           (with +++ front matter: date, country, lat, lon, …)
              media/
                *.jpg / *.png / *.mp4 …
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[import]
    except ImportError:
        import tomli as tomllib  # type: ignore[import,no-redef]

from echotrail_gen.geo import gpx_to_geojson, load_geojson

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov"}

_FRONTMATTER_RE = re.compile(
    r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)", re.DOTALL
)


def _read_text(path: Path) -> str:
    """Return stripped text content of *path*, or empty string if missing."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse TOML front matter delimited by ``+++`` from *text*.

    Returns ``(metadata_dict, body_text)``.  If no valid front matter is
    found the full text is returned as the body with an empty dict.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    toml_str = m.group(1)
    body = m.group(2).strip()
    try:
        meta = tomllib.loads(toml_str)
    except Exception as exc:
        log.warning("Failed to parse TOML front matter: %s", exc)
        return {}, text
    return meta, body


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

_ENTRY_KNOWN_KEYS = {"date", "country", "weather", "temperature_c", "lat", "lon", "point_name"}


def load_entry(entry_dir: Path, trip_id: str) -> dict[str, Any]:
    """Load one entry directory and return a descriptor dict."""
    entry_id = entry_dir.name

    # Read text.md with front matter
    raw_text = _read_text(entry_dir / "text.md")
    meta, text_md = _parse_frontmatter(raw_text)

    # Core fields from front matter
    date = str(meta.get("date", ""))
    country = str(meta.get("country", ""))
    weather = str(meta.get("weather", ""))
    temperature_c = str(meta.get("temperature_c", "")) if "temperature_c" in meta else ""

    # Point geometry from front matter lat/lon
    lat = meta.get("lat")
    lon = meta.get("lon")
    point_name = str(meta.get("point_name", ""))

    point_geojson: dict[str, Any] | None = None
    if lat is not None and lon is not None:
        props: dict[str, Any] = {}
        if point_name:
            props["name"] = point_name
        point_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)],
            },
            "properties": props,
        }

    # Optional meta.json (future-proofing)
    meta_json: dict[str, Any] = {}
    meta_path = entry_dir / "meta.json"
    if meta_path.exists():
        try:
            meta_json = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not parse %s: %s", meta_path, exc)

    # Extra front matter keys (anything not in the known set)
    extra = {k: str(v) for k, v in meta.items() if k not in _ENTRY_KNOWN_KEYS}

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

_TRIP_KNOWN_KEYS = {"title", "odometer_km"}


def load_trip(trip_dir: Path) -> dict[str, Any]:
    """Load one trip directory and return a descriptor dict."""
    trip_id = trip_dir.name

    # Read description.md with front matter
    raw_desc = _read_text(trip_dir / "description.md")
    meta, description_md = _parse_frontmatter(raw_desc)

    title = str(meta.get("title", "")) or trip_id
    odometer_km = str(meta.get("odometer_km", "")) if "odometer_km" in meta else ""

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

    # Extra front matter keys
    extra = {k: str(v) for k, v in meta.items() if k not in _TRIP_KNOWN_KEYS}

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
