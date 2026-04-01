"""Shared fixtures for EchoTrail tests."""

from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DATA = REPO_ROOT / "example_data"


def _create_test_jpeg(path: Path, width: int = 800, height: int = 600) -> None:
    """Create a minimal real JPEG so Pillow can process it."""
    img = Image.new("RGB", (width, height), color=(120, 180, 60))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG", quality=80)


# ---------------------------------------------------------------------------
# Minimal templates (just enough to test rendering)
# ---------------------------------------------------------------------------

@pytest.fixture()
def templates_dir(tmp_path: Path) -> Path:
    """Create a minimal set of Jinja2 templates in a temp directory.

    Copies the bundled default templates so integration tests exercise
    actual markup.
    """
    from echotrail_gen.builder import _bundled_templates

    tpl = tmp_path / "templates"
    tpl.mkdir()
    for f in _bundled_templates().glob("*.html"):
        shutil.copy2(f, tpl / f.name)
    return tpl


# ---------------------------------------------------------------------------
# Minimal assets directory (no real Leaflet, just structure)
# ---------------------------------------------------------------------------

@pytest.fixture()
def assets_dir(tmp_path: Path) -> Path:
    """Create a minimal assets tree."""
    assets = tmp_path / "assets"
    css = assets / "css"
    css.mkdir(parents=True)
    (css / "style.css").write_text("body { margin: 0; }", encoding="utf-8")
    vendor = assets / "vendor" / "leaflet"
    vendor.mkdir(parents=True)
    (vendor / "leaflet.js").write_text("/* stub */", encoding="utf-8")
    (vendor / "leaflet.css").write_text("/* stub */", encoding="utf-8")
    (vendor / "images").mkdir()
    glightbox = assets / "vendor" / "glightbox"
    (glightbox / "js").mkdir(parents=True)
    (glightbox / "css").mkdir(parents=True)
    (glightbox / "js" / "glightbox.min.js").write_text("/* stub */", encoding="utf-8")
    (glightbox / "css" / "glightbox.min.css").write_text("/* stub */", encoding="utf-8")
    return assets


@pytest.fixture()
def example_data_dir() -> Path:
    """Return the path to the shipped example data."""
    return EXAMPLE_DATA


# ---------------------------------------------------------------------------
# Sample data tree (TOML front matter format)
# ---------------------------------------------------------------------------

SAMPLE_TRIP_DESC = textwrap.dedent("""\
    +++
    title = 'Test-Tour 2026'
    odometer_km = '1.200'
    vehicle = 'Honda CB 500X'
    +++

    # Test-Tour 2026

    A short test trip.
""")

SAMPLE_ENTRY_BERLIN = textwrap.dedent("""\
    +++
    date = 2026-03-31
    country = 'Germany'
    weather = 'Cloudy'
    temperature_c = 9
    lat = 52.52
    lon = 13.405
    point_name = 'Berlin – Start'
    +++

    # Departure from Berlin

    Early morning departure. **Fantastic**.
""")

SAMPLE_ENTRY_PRAGUE = textwrap.dedent("""\
    +++
    date = 2026-04-05
    country = 'Czechia'
    lat = 50.0755
    lon = 14.4376
    +++

    # Prague in the Morning Light

    The golden city.
""")

SAMPLE_ROUTE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [13.405, 52.52],
                    [14.4376, 50.0755],
                ],
            },
            "properties": {"name": "Test Route"},
        }
    ],
}


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """Create a sample data tree with one trip and two entries."""
    data = tmp_path / "data"
    trip = data / "trips" / "2026-test-tour"
    entry_berlin = trip / "entries" / "2026-03-31-berlin"
    entry_prague = trip / "entries" / "2026-04-05-prague"

    entry_berlin.mkdir(parents=True)
    entry_prague.mkdir(parents=True)

    # Trip description + route
    (trip / "description.md").write_text(SAMPLE_TRIP_DESC, encoding="utf-8")
    (trip / "route.geojson").write_text(
        json.dumps(SAMPLE_ROUTE_GEOJSON), encoding="utf-8"
    )

    # Berlin entry with media
    (entry_berlin / "text.md").write_text(SAMPLE_ENTRY_BERLIN, encoding="utf-8")
    media = entry_berlin / "media"
    media.mkdir()
    _create_test_jpeg(media / "foto1.jpg", 2000, 1500)
    (media / "clip.mp4").write_bytes(b"\x00\x00fake-mp4")
    (entry_berlin / "media.json").write_text(
        json.dumps(
            {
                "media": [
                    {"name": "foto1.jpg", "description": "Berlin TV Tower at sunrise"},
                    {"name": "clip.mp4", "description": "Morning traffic time-lapse"},
                ]
            }
        ),
        encoding="utf-8",
    )

    # Prague entry (no media)
    (entry_prague / "text.md").write_text(SAMPLE_ENTRY_PRAGUE, encoding="utf-8")

    return data
