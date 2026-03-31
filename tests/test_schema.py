"""Tests for echotrail_gen.schema – data loading layer."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from echotrail_gen.schema import (
    _parse_frontmatter,
    _media_files,
    load_entry,
    load_trip,
    load_all_trips,
)


# ── _parse_frontmatter ─────────────────────────────────────────────────────

class TestParseFrontmatter:
    def test_valid_toml(self):
        text = textwrap.dedent("""\
            +++
            title = 'Hallo'
            count = 42
            +++

            Body text here.
        """)
        meta, body = _parse_frontmatter(text)
        assert meta["title"] == "Hallo"
        assert meta["count"] == 42
        assert body == "Body text here."

    def test_no_frontmatter(self):
        text = "Just plain text.\nNo delimiters."
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_empty_frontmatter(self):
        # Empty frontmatter (no content between +++ delimiters) does not
        # match the regex, so the full text is returned as body.
        text = "+++\n+++\nBody only."
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_date_value(self):
        text = "+++\ndate = 2026-03-31\n+++\nText."
        meta, body = _parse_frontmatter(text)
        # TOML native dates are datetime.date objects
        from datetime import date
        assert meta["date"] == date(2026, 3, 31)


# ── _media_files ────────────────────────────────────────────────────────────

class TestMediaFiles:
    def test_mixed_files(self, tmp_path: Path):
        media = tmp_path / "media"
        media.mkdir()
        (media / "a.jpg").write_bytes(b"img")
        (media / "b.mp4").write_bytes(b"vid")
        (media / "c.png").write_bytes(b"img")
        (media / "readme.txt").write_bytes(b"skip")

        result = _media_files(media)
        assert len(result) == 3
        assert result[0] == {"type": "image", "name": "a.jpg"}
        assert result[1] == {"type": "video", "name": "b.mp4"}
        assert result[2] == {"type": "image", "name": "c.png"}

    def test_nonexistent_dir(self, tmp_path: Path):
        result = _media_files(tmp_path / "nope")
        assert result == []

    def test_empty_dir(self, tmp_path: Path):
        media = tmp_path / "media"
        media.mkdir()
        assert _media_files(media) == []


# ── load_entry ──────────────────────────────────────────────────────────────

class TestLoadEntry:
    def test_full_entry(self, data_dir: Path):
        entry_dir = data_dir / "trips" / "2026-test-tour" / "entries" / "2026-03-31-berlin"
        entry = load_entry(entry_dir, "2026-test-tour")

        assert entry["id"] == "2026-03-31-berlin"
        assert entry["trip_id"] == "2026-test-tour"
        assert entry["date"] == "2026-03-31"
        assert entry["country"] == "Deutschland"
        assert entry["weather"] == "Bewölkt"
        assert entry["temperature_c"] == "9"
        assert "Aufbruch" in entry["text_md"]

        # Point GeoJSON generated from lat/lon
        assert entry["point_geojson"] is not None
        coords = entry["point_geojson"]["geometry"]["coordinates"]
        assert coords == [13.405, 52.52]
        assert entry["point_geojson"]["properties"]["name"] == "Berlin – Start"

        # JSON serialisation
        assert '"Point"' in entry["point_geojson_json"]

        # Media
        assert len(entry["media"]) == 2
        names = [m["name"] for m in entry["media"]]
        assert "foto1.jpg" in names
        assert "clip.mp4" in names

        # URL
        assert entry["url"] == "trips/2026-test-tour/entries/2026-03-31-berlin/"

    def test_minimal_entry(self, tmp_path: Path):
        entry_dir = tmp_path / "minimal"
        entry_dir.mkdir()
        (entry_dir / "text.md").write_text(
            "+++\ndate = 2026-01-01\n+++\nHello.", encoding="utf-8"
        )
        entry = load_entry(entry_dir, "trip-x")

        assert entry["date"] == "2026-01-01"
        assert entry["country"] == ""
        assert entry["weather"] == ""
        assert entry["temperature_c"] == ""
        assert entry["point_geojson"] is None
        assert entry["point_geojson_json"] == "null"
        assert entry["media"] == []
        assert entry["text_md"] == "Hello."

    def test_extra_keys(self, tmp_path: Path):
        entry_dir = tmp_path / "extra"
        entry_dir.mkdir()
        (entry_dir / "text.md").write_text(
            "+++\ndate = 2026-01-01\nfuel_liters = 12\n+++\n", encoding="utf-8"
        )
        entry = load_entry(entry_dir, "t")
        assert "fuel_liters" in entry["extra"]
        assert entry["extra"]["fuel_liters"] == "12"


# ── load_trip ───────────────────────────────────────────────────────────────

class TestLoadTrip:
    def test_full_trip(self, data_dir: Path):
        trip_dir = data_dir / "trips" / "2026-test-tour"
        trip = load_trip(trip_dir)

        assert trip["id"] == "2026-test-tour"
        assert trip["title"] == "Test-Tour 2026"
        assert trip["odometer_km"] == "1.200"
        assert "Testreise" in trip["description_md"]

        # Route
        assert trip["route_geojson"] is not None
        assert trip["route_geojson"]["type"] == "FeatureCollection"
        assert '"LineString"' in trip["route_geojson_json"]

        # Entries loaded and sorted
        assert len(trip["entries"]) == 2
        assert trip["entries"][0]["id"] == "2026-03-31-berlin"
        assert trip["entries"][1]["id"] == "2026-04-05-prag"

        # Extra keys
        assert trip["extra"]["vehicle"] == "Honda CB 500X"

        # URL
        assert trip["url"] == "trips/2026-test-tour/"

    def test_trip_no_route(self, tmp_path: Path):
        trip_dir = tmp_path / "no-route"
        trip_dir.mkdir()
        (trip_dir / "description.md").write_text(
            "+++\ntitle = 'Leer'\n+++\nNix.", encoding="utf-8"
        )
        trip = load_trip(trip_dir)
        assert trip["route_geojson"] is None
        assert trip["route_geojson_json"] == "null"
        assert trip["entries"] == []

    def test_trip_no_entries(self, data_dir: Path):
        """Trip with route but entries dir removed."""
        trip_dir = data_dir / "trips" / "2026-test-tour"
        import shutil
        shutil.rmtree(trip_dir / "entries")
        trip = load_trip(trip_dir)
        assert trip["entries"] == []
        assert trip["route_geojson"] is not None

    def test_trip_gpx_fallback(self, tmp_path: Path):
        trip_dir = tmp_path / "gpx-trip"
        trip_dir.mkdir()
        (trip_dir / "description.md").write_text(
            "+++\ntitle = 'GPX Trip'\n+++\n", encoding="utf-8"
        )
        gpx_content = textwrap.dedent("""\
            <?xml version="1.0"?>
            <gpx version="1.1">
              <trk>
                <name>Route</name>
                <trkseg>
                  <trkpt lat="52.52" lon="13.405"/>
                  <trkpt lat="50.07" lon="14.44"/>
                </trkseg>
              </trk>
            </gpx>
        """)
        (trip_dir / "route.gpx").write_text(gpx_content, encoding="utf-8")
        trip = load_trip(trip_dir)
        assert trip["route_geojson"] is not None
        feat = trip["route_geojson"]["features"][0]
        assert feat["geometry"]["type"] == "LineString"


# ── load_all_trips ──────────────────────────────────────────────────────────

class TestLoadAllTrips:
    def test_loads_trips(self, data_dir: Path):
        trips = load_all_trips(data_dir)
        assert len(trips) == 1
        assert trips[0]["id"] == "2026-test-tour"

    def test_empty_data_dir(self, tmp_path: Path):
        data = tmp_path / "empty"
        data.mkdir()
        trips = load_all_trips(data)
        assert trips == []
