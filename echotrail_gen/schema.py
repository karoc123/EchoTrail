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
                            media.json        (optional media metadata, e.g. image descriptions)
              media/
                *.jpg / *.png / *.mp4 …
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import tomllib
from pydantic import BaseModel, ConfigDict, Field, field_validator

from echotrail_gen.images import thumb_name as _thumb_name

from echotrail_gen.geo import gpx_to_geojson, load_geojson

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class MediaItem(BaseModel):
    """Media file descriptor for an entry."""

    model_config = ConfigDict(frozen=True)

    type: Literal["image", "video"]
    name: str
    thumb_name: str = ""
    description: str = ""


class Entry(BaseModel):
    """One journal entry / waypoint."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str
    trip_id: str
    url: str
    title: str = ""
    date: str
    text_md: str
    country: str = ""
    country_flag: str = ""
    weather: str = ""
    temperature_c: str = ""
    point_geojson: dict[str, Any] | None = None
    point_geojson_json: str = "null"
    media: list[MediaItem] = []
    extra: dict[str, str] = {}
    meta: dict[str, Any] = {}


class Trip(BaseModel):
    """One trip with associated entries."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str
    url: str
    title: str
    description_md: str
    odometer_km: str = ""
    cover: str | None = None
    route_geojson: dict[str, Any] | None = None
    route_geojson_json: str = "null"
    entries: list[Entry]
    visited_countries: list[dict[str, str]] = []
    start_date: str = ""
    """Date of first entry in ISO format (YYYY-MM-DD), used for sorting."""
    duration_days: int = 0
    """Number of days between first and last entry (inclusive)."""
    extra: dict[str, str] = {}
    meta: dict[str, Any] = {}
    source_dir: Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov"}

_FRONTMATTER_RE = re.compile(
    r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)", re.DOTALL
)

_COUNTRY_TO_CODE = {
    # Germany
    "germany": "DE",
    "deutschland": "DE",
    # Sweden
    "sweden": "SE",
    "schweden": "SE",
    # Norway
    "norway": "NO",
    "norwegen": "NO",
    # Czechia
    "czechia": "CZ",
    "czech republic": "CZ",
    "tschechien": "CZ",
    "tschechische republik": "CZ",
    # Austria
    "austria": "AT",
    "osterreich": "AT",
    "oesterreich": "AT",
    # Switzerland
    "switzerland": "CH",
    "schweiz": "CH",
    # Denmark
    "denmark": "DK",
    "danemark": "DK",
    "danemark": "DK",
    # Finland
    "finland": "FI",
    "finnland": "FI",
    # Netherlands
    "netherlands": "NL",
    "the netherlands": "NL",
    "niederlande": "NL",
    "holland": "NL",
    # France
    "france": "FR",
    "frankreich": "FR",
    # Italy
    "italy": "IT",
    "italien": "IT",
    # Spain
    "spain": "ES",
    "spanien": "ES",
    # Portugal
    "portugal": "PT",
    # Poland
    "poland": "PL",
    "polen": "PL",
    # Belgium
    "belgium": "BE",
    "belgien": "BE",
    # United Kingdom
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "great britain": "GB",
    "grossbritannien": "GB",
    # Ireland
    "ireland": "IE",
    "irland": "IE",
    # Iceland
    "iceland": "IS",
    "island": "IS",
    # Estonia
    "estonia": "EE",
    "estland": "EE",
    # Latvia
    "latvia": "LV",
    "lettland": "LV",
    # Lithuania
    "lithuania": "LT",
    "litauen": "LT",
    # Slovakia
    "slovakia": "SK",
    "slowakei": "SK",
    "slovak republic": "SK",
    # Hungary
    "hungary": "HU",
    "ungarn": "HU",
    # Romania
    "romania": "RO",
    "rumanien": "RO",
    # Bulgaria
    "bulgaria": "BG",
    "bulgarien": "BG",
    # Croatia
    "croatia": "HR",
    "kroatien": "HR",
    # Slovenia
    "slovenia": "SI",
    "slowenien": "SI",
    # Serbia
    "serbia": "RS",
    "serbien": "RS",
    # Bosnia and Herzegovina
    "bosnia and herzegovina": "BA",
    "bosnia": "BA",
    "bosnien": "BA",
    "bosnien und herzegowina": "BA",
    # Montenegro
    "montenegro": "ME",
    # North Macedonia
    "north macedonia": "MK",
    "nordmazedonien": "MK",
    "macedonia": "MK",
    # Albania
    "albania": "AL",
    "albanien": "AL",
    # Greece
    "greece": "GR",
    "griechenland": "GR",
    # Cyprus
    "cyprus": "CY",
    "zypern": "CY",
    # Malta
    "malta": "MT",
    # Luxembourg
    "luxembourg": "LU",
    "luxemburg": "LU",
    # Liechtenstein
    "liechtenstein": "LI",
    # Monaco
    "monaco": "MC",
    # San Marino
    "san marino": "SM",
    # Andorra
    "andorra": "AD",
    # Belarus
    "belarus": "BY",
    "weissrussland": "BY",
    "weißrussland": "BY",
    # Ukraine
    "ukraine": "UA",
    # Russia
    "russia": "RU",
    "russland": "RU",
    "russian federation": "RU",
    # Moldova
    "moldova": "MD",
    "moldau": "MD",
    # Georgia
    "georgia": "GE",
    "georgien": "GE",
    # Armenia
    "armenia": "AM",
    "armenien": "AM",
    # Azerbaijan
    "azerbaijan": "AZ",
    "aserbaidschan": "AZ",
    # Turkey
    "turkey": "TR",
    "turkiye": "TR",
    "turkei": "TR",
    "turchei": "TR",
    # Kosovo
    "kosovo": "XK",
    # USA
    "usa": "US",
    "united states": "US",
    "united states of america": "US",
    # Canada
    "canada": "CA",
    "kanada": "CA",
    # Mexico
    "mexico": "MX",
    "mexiko": "MX",
    # Brazil
    "brazil": "BR",
    "brasilien": "BR",
    # Argentina
    "argentina": "AR",
    "argentinien": "AR",
    # Chile
    "chile": "CL",
    # Colombia
    "colombia": "CO",
    "kolumbien": "CO",
    # Peru
    "peru": "PE",
    # Japan
    "japan": "JP",
    # China
    "china": "CN",
    "volksrepublik china": "CN",
    # South Korea
    "south korea": "KR",
    "korea": "KR",
    "sudkorea": "KR",
    # India
    "india": "IN",
    "indien": "IN",
    # Australia
    "australia": "AU",
    "australien": "AU",
    # New Zealand
    "new zealand": "NZ",
    "neuseeland": "NZ",
    # South Africa
    "south africa": "ZA",
    "sudafrika": "ZA",
    # Egypt
    "egypt": "EG",
    "agypten": "EG",
    # Morocco
    "morocco": "MA",
    "marokko": "MA",
    # Tunisia
    "tunisia": "TN",
    "tunesien": "TN",
    # Kenya
    "kenya": "KE",
    "kenia": "KE",
    # Nigeria
    "nigeria": "NG",
    # Thailand
    "thailand": "TH",
    # Vietnam
    "vietnam": "VN",
    # Indonesia
    "indonesia": "ID",
    "indonesien": "ID",
    # Malaysia
    "malaysia": "MY",
    # Singapore
    "singapore": "SG",
    "singapur": "SG",
    # Philippines
    "philippines": "PH",
    "philippinen": "PH",
    # Saudi Arabia
    "saudi arabia": "SA",
    "saudi-arabien": "SA",
    # United Arab Emirates
    "united arab emirates": "AE",
    "uae": "AE",
    "vereinigte arabische emirate": "AE",
    # Israel
    "israel": "IL",
    # Kazakhstan
    "kazakhstan": "KZ",
    "kasachstan": "KZ",
}


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


def _normalize_country_key(country: str) -> str:
    """Normalize country names for robust lookup."""
    normalized = unicodedata.normalize("NFKD", country)
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    ascii_only = ascii_only.lower()
    ascii_only = re.sub(r"[^a-z\s]", " ", ascii_only)
    return re.sub(r"\s+", " ", ascii_only).strip()


def _country_code_to_flag(code: str) -> str:
    """Convert ISO-3166 alpha-2 code to unicode flag emoji."""
    if len(code) != 2 or not code.isalpha():
        return ""
    code = code.upper()
    base = 127397
    return chr(base + ord(code[0])) + chr(base + ord(code[1]))


def country_to_flag(country: str) -> str:
    """Return emoji flag for a country name or ISO code."""
    if not country:
        return ""

    raw = country.strip()
    if len(raw) == 2 and raw.isalpha():
        return _country_code_to_flag(raw)

    code = _COUNTRY_TO_CODE.get(_normalize_country_key(raw), "")
    if not code:
        return ""
    return _country_code_to_flag(code)


def _visited_countries(entries: list[Entry]) -> list[dict[str, str]]:
    """Return unique countries in entry order, each with resolved flag."""
    seen: set[str] = set()
    countries: list[dict[str, str]] = []
    for entry in entries:
        name = entry.country.strip()
        if not name:
            continue
        key = _normalize_country_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        countries.append({"name": name, "flag": country_to_flag(name)})
    return countries


def _media_files(media_dir: Path, descriptions: dict[str, str] | None = None) -> list[MediaItem]:
    """Return sorted list of media file descriptors from *media_dir*."""
    if not media_dir.is_dir():
        return []
    descriptions = descriptions or {}
    files: list[MediaItem] = []
    for p in sorted(media_dir.iterdir()):
        ext = p.suffix.lower()
        if ext in _IMAGE_EXTS:
            files.append(
                MediaItem(
                    type="image",
                    name=p.name,
                    thumb_name=_thumb_name(p.name),
                    description=descriptions.get(p.name, ""),
                )
            )
        elif ext in _VIDEO_EXTS:
            files.append(
                MediaItem(
                    type="video",
                    name=p.name,
                    description=descriptions.get(p.name, ""),
                )
            )
    return files


def _media_descriptions(entry_dir: Path) -> dict[str, str]:
    """Load media descriptions from optional ``media.json`` in *entry_dir*."""
    media_meta_path = entry_dir / "media.json"
    if not media_meta_path.exists():
        return {}

    try:
        payload = json.loads(media_meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Could not parse %s: %s", media_meta_path, exc)
        return {}

    if isinstance(payload, dict):
        raw_items = payload.get("media", payload.get("items", []))
    elif isinstance(payload, list):
        raw_items = payload
    else:
        return {}

    descriptions: dict[str, str] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        description = str(item.get("description", "")).strip()
        descriptions[name] = description
    return descriptions


def _trip_duration(entries: list[Entry]) -> tuple[str, int]:
    """Calculate trip start date and duration in days.
    
    Returns (start_date_iso, duration_days).
    - start_date_iso: ISO format YYYY-MM-DD of first entry, or "" if no entries
    - duration_days: Number of days from first to last entry (inclusive)
    """
    if not entries:
        return "", 0
    
    # Get all valid dates from entries
    dates = []
    for entry in entries:
        if entry.date and entry.date.strip():
            try:
                # Parse as ISO date (YYYY-MM-DD)
                date_obj = datetime.fromisoformat(entry.date.strip())
                dates.append((entry.date.strip(), date_obj))
            except (ValueError, TypeError):
                pass
    
    if not dates:
        return "", 0
    
    # Sort by date
    dates.sort(key=lambda x: x[1])
    start_date_str = dates[0][0]
    end_date_obj = dates[-1][1]
    start_date_obj = dates[0][1]
    
    # Calculate duration in days (inclusive: +1)
    duration_days = (end_date_obj - start_date_obj).days + 1
    
    return start_date_str, duration_days


# ---------------------------------------------------------------------------
# Entry loader
# ---------------------------------------------------------------------------

_ENTRY_KNOWN_KEYS = {"date", "country", "weather", "temperature_c", "lat", "lon", "point_name"}

_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def load_entry(entry_dir: Path, trip_id: str, skip_videos: bool = False) -> Entry:
    """Load one entry directory and return an Entry model."""
    entry_id = entry_dir.name

    # Read text.md with front matter
    raw_text = _read_text(entry_dir / "text.md")
    meta, text_md = _parse_frontmatter(raw_text)

    # Core fields from front matter
    date_val = meta.get("date", "")
    date = str(date_val) if date_val is not None else ""
    country = str(meta.get("country", ""))
    country_flag = country_to_flag(country)
    weather = str(meta.get("weather", ""))
    temperature_c = str(meta.get("temperature_c", "")) if "temperature_c" in meta else ""

    # Entry title: prefer first # heading from body, then point_name
    heading_match = _HEADING_RE.search(text_md)
    title = heading_match.group(1).strip() if heading_match else str(meta.get("point_name", ""))

    # Point geometry from front matter lat/lon
    lat = meta.get("lat")
    lon = meta.get("lon")
    point_name = str(meta.get("point_name", ""))

    point_geojson: dict[str, Any] | None = None
    if lat is not None and lon is not None:
        # Convert and validate coordinates
        try:
            lat_float = float(lat)
            lon_float = float(lon)

            # Validate coordinate ranges
            if not (-90 <= lat_float <= 90):
                log.warning(
                    "Invalid latitude %s in %s: must be between -90 and 90. Skipping coordinates.",
                    lat_float, entry_dir
                )
            elif not (-180 <= lon_float <= 180):
                log.warning(
                    "Invalid longitude %s in %s: must be between -180 and 180. Skipping coordinates.",
                    lon_float, entry_dir
                )
            else:
                props: dict[str, Any] = {}
                if point_name:
                    props["name"] = point_name
                point_geojson = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon_float, lat_float],
                    },
                    "properties": props,
                }
        except (ValueError, TypeError) as e:
            log.warning("Invalid coordinates in %s: %s. Skipping.", entry_dir, e)

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
    media = _media_files(
        entry_dir / "media",
        descriptions=_media_descriptions(entry_dir),
    )
    
    # Filter out videos if requested
    if skip_videos:
        media = [m for m in media if m.type != "video"]

    return Entry(
        id=entry_id,
        trip_id=trip_id,
        url=f"trips/{trip_id}/entries/{entry_id}/",
        title=title,
        date=date,
        text_md=text_md,
        country=country,
        country_flag=country_flag,
        weather=weather,
        temperature_c=temperature_c,
        point_geojson=point_geojson,
        point_geojson_json=json.dumps(point_geojson) if point_geojson else "null",
        media=media,
        extra=extra,
        meta=meta_json,
    )


# ---------------------------------------------------------------------------
# Trip loader
# ---------------------------------------------------------------------------

_TRIP_KNOWN_KEYS = {"title", "odometer_km"}


def load_trip(trip_dir: Path, skip_videos: bool = False) -> Trip:
    """Load one trip directory and return a Trip model."""
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
    entries: list[Entry] = []
    if entries_dir.is_dir():
        for entry_dir in sorted(entries_dir.iterdir()):
            if entry_dir.is_dir():
                entries.append(load_entry(entry_dir, trip_id, skip_videos=skip_videos))

    visited_countries = _visited_countries(entries)
    start_date, duration_days = _trip_duration(entries)

    return Trip(
        id=trip_id,
        url=f"trips/{trip_id}/",
        title=title,
        description_md=description_md,
        odometer_km=odometer_km,
        cover=cover,
        route_geojson=route_geojson,
        route_geojson_json=json.dumps(route_geojson) if route_geojson else "null",
        entries=entries,
        visited_countries=visited_countries,
        start_date=start_date,
        duration_days=duration_days,
        extra=extra,
        meta=meta_json,
        source_dir=trip_dir.resolve(),
    )


# ---------------------------------------------------------------------------
# Top-level loader
# ---------------------------------------------------------------------------


def load_all_trips(data_dir: Path, skip_videos: bool = False) -> list[Trip]:
    """Load every trip found under *data_dir/trips/* and return a list.
    
    When *skip_videos* is True, video files are excluded from media galleries.
    
    Trips are sorted by start_date in descending order (newest first).
    """
    trips_root = data_dir / "trips"
    if not trips_root.is_dir():
        log.warning("No trips directory found at %s", trips_root)
        return []

    trips: list[Trip] = []
    for trip_dir in sorted(trips_root.iterdir()):
        if trip_dir.is_dir():
            log.info("Loading trip: %s", trip_dir.name)
            trips.append(load_trip(trip_dir, skip_videos=skip_videos))
    
    # Sort by start_date descending (newest first)
    trips.sort(key=lambda t: t.start_date, reverse=True)
    return trips
