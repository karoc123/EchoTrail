"""Shared fixtures for EchoTrail tests."""

from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Minimal templates (just enough to test rendering)
# ---------------------------------------------------------------------------

@pytest.fixture()
def templates_dir(tmp_path: Path) -> Path:
    """Create a minimal set of Jinja2 templates in a temp directory."""
    tpl = tmp_path / "templates"
    tpl.mkdir()

    # Copy the real templates so integration tests exercise actual markup.
    real_tpl = Path(__file__).resolve().parent.parent / "templates"
    for f in real_tpl.glob("*.html"):
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
    return assets


# ---------------------------------------------------------------------------
# Sample data tree
# ---------------------------------------------------------------------------

SAMPLE_TRIP_DESC = textwrap.dedent("""\
    +++
    title = 'Test-Tour 2026'
    odometer_km = '1.200'
    vehicle = 'Honda CB 500X'
    +++

    # Test-Tour 2026

    Eine kurze Testreise.
""")

SAMPLE_ENTRY_BERLIN = textwrap.dedent("""\
    +++
    date = 2026-03-31
    country = 'Deutschland'
    weather = 'Bewölkt'
    temperature_c = 9
    lat = 52.52
    lon = 13.405
    point_name = 'Berlin – Start'
    +++

    # Aufbruch aus Berlin

    Früh morgens los. **Großartig**.
""")

SAMPLE_ENTRY_PRAG = textwrap.dedent("""\
    +++
    date = 2026-04-05
    country = 'Tschechien'
    lat = 50.0755
    lon = 14.4376
    +++

    # Prag im Morgenlicht

    Goldene Stadt.
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
            "properties": {"name": "Testroute"},
        }
    ],
}


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """Create a sample data tree with one trip and two entries."""
    data = tmp_path / "data"
    trip = data / "trips" / "2026-test-tour"
    entry_berlin = trip / "entries" / "2026-03-31-berlin"
    entry_prag = trip / "entries" / "2026-04-05-prag"

    entry_berlin.mkdir(parents=True)
    entry_prag.mkdir(parents=True)

    # Trip description + route
    (trip / "description.md").write_text(SAMPLE_TRIP_DESC, encoding="utf-8")
    (trip / "route.geojson").write_text(
        json.dumps(SAMPLE_ROUTE_GEOJSON), encoding="utf-8"
    )

    # Berlin entry with media
    (entry_berlin / "text.md").write_text(SAMPLE_ENTRY_BERLIN, encoding="utf-8")
    media = entry_berlin / "media"
    media.mkdir()
    (media / "foto1.jpg").write_bytes(b"\xff\xd8fake-jpg")
    (media / "clip.mp4").write_bytes(b"\x00\x00fake-mp4")

    # Prag entry (no media)
    (entry_prag / "text.md").write_text(SAMPLE_ENTRY_PRAG, encoding="utf-8")

    return data
