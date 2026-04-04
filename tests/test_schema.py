"""Tests for tracevoyage_gen.schema – data loading layer."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from tracevoyage_gen.schema import (
    _parse_frontmatter,
    _media_files,
    country_to_flag,
    load_entry,
    load_trip,
    load_all_trips,
)


# ── _parse_frontmatter ─────────────────────────────────────────────────────

class TestParseFrontmatter:
    def test_valid_toml(self):
        text = textwrap.dedent("""\
            +++
            title = 'Hello'
            count = 42
            +++

            Body text here.
        """)
        meta, body = _parse_frontmatter(text)
        assert meta["title"] == "Hello"
        assert meta["count"] == 42
        assert body == "Body text here."

    def test_no_frontmatter(self):
        text = "Just plain text.\nNo delimiters."
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_empty_frontmatter(self):
        text = "+++\n+++\nBody only."
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_date_value(self):
        text = "+++\ndate = 2026-03-31\n+++\nText."
        meta, body = _parse_frontmatter(text)
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
        assert result[0].type == "image" and result[0].name == "a.jpg"
        assert result[0].thumb_name == "thumb_a.jpg"
        assert result[1].type == "video" and result[1].name == "b.mp4"
        assert result[1].thumb_name == ""
        assert result[2].type == "image" and result[2].name == "c.png"
        assert result[2].thumb_name == "thumb_c.jpg"

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

        assert entry.id == "2026-03-31-berlin"
        assert entry.trip_id == "2026-test-tour"
        assert entry.date == "2026-03-31"
        assert entry.country == "Germany"
        assert entry.country_flag == "🇩🇪"
        assert entry.weather == "Cloudy"
        assert entry.temperature_c == "9"
        assert "Departure" in entry.text_md

        # Point GeoJSON generated from lat/lon
        assert entry.point_geojson is not None
        coords = entry.point_geojson["geometry"]["coordinates"]
        assert coords == [13.405, 52.52]
        assert entry.point_geojson["properties"]["name"] == "Berlin – Start"

        # JSON serialisation
        assert '"Point"' in entry.point_geojson_json

        # Media
        assert len(entry.media) == 2
        names = [m.name for m in entry.media]
        assert "foto1.jpg" in names
        assert "clip.mp4" in names
        media_by_name = {m.name: m for m in entry.media}
        assert media_by_name["foto1.jpg"].description == "Berlin TV Tower at sunrise"
        assert media_by_name["clip.mp4"].description == "Morning traffic time-lapse"

        # URL
        assert entry.url == "trips/2026-test-tour/entries/2026-03-31-berlin/"

    def test_minimal_entry(self, tmp_path: Path):
        entry_dir = tmp_path / "minimal"
        entry_dir.mkdir()
        (entry_dir / "text.md").write_text(
            "+++\ndate = 2026-01-01\n+++\nHello.", encoding="utf-8"
        )
        entry = load_entry(entry_dir, "trip-x")

        assert entry.date == "2026-01-01"
        assert entry.country == ""
        assert entry.weather == ""
        assert entry.temperature_c == ""
        assert entry.point_geojson is None
        assert entry.point_geojson_json == "null"
        assert entry.media == []
        assert entry.text_md == "Hello."

    def test_entry_ignores_invalid_media_json(self, tmp_path: Path):
        entry_dir = tmp_path / "invalid-media"
        entry_dir.mkdir()
        (entry_dir / "text.md").write_text(
            "+++\ndate = 2026-01-01\n+++\nHello.", encoding="utf-8"
        )
        media_dir = entry_dir / "media"
        media_dir.mkdir()
        (media_dir / "x.jpg").write_bytes(b"img")
        (entry_dir / "media.json").write_text("{broken", encoding="utf-8")

        entry = load_entry(entry_dir, "trip-x")
        assert len(entry.media) == 1
        assert entry.media[0].description == ""

    def test_entry_excludes_videos_when_requested(self, data_dir: Path):
        entry_dir = data_dir / "trips" / "2026-test-tour" / "entries" / "2026-03-31-berlin"
        entry = load_entry(entry_dir, "2026-test-tour", skip_videos=True)

        assert len(entry.media) == 1
        assert entry.media[0].type == "image"
        assert entry.media[0].name == "foto1.jpg"

    def test_extra_keys(self, tmp_path: Path):
        entry_dir = tmp_path / "extra"
        entry_dir.mkdir()
        (entry_dir / "text.md").write_text(
            "+++\ndate = 2026-01-01\nfuel_liters = 12\n+++\n", encoding="utf-8"
        )
        entry = load_entry(entry_dir, "t")
        assert "fuel_liters" in entry.extra
        assert entry.extra["fuel_liters"] == "12"


# ── load_trip ───────────────────────────────────────────────────────────────

class TestLoadTrip:
    def test_full_trip(self, data_dir: Path):
        trip_dir = data_dir / "trips" / "2026-test-tour"
        trip = load_trip(trip_dir)

        assert trip.id == "2026-test-tour"
        assert trip.title == "Test-Tour 2026"
        assert trip.odometer_km == "1.200"
        assert "test trip" in trip.description_md

        # Route
        assert trip.route_geojson is not None
        assert trip.route_geojson["type"] == "FeatureCollection"
        assert '"LineString"' in trip.route_geojson_json

        # Entries loaded and sorted
        assert len(trip.entries) == 2
        assert trip.entries[0].id == "2026-03-31-berlin"
        assert trip.entries[1].id == "2026-04-05-prague"
        assert [c["name"] for c in trip.visited_countries] == ["Germany", "Czechia"]
        assert [c["flag"] for c in trip.visited_countries] == ["🇩🇪", "🇨🇿"]

        # Duration and start date
        assert trip.start_date == "2026-03-31"
        assert trip.duration_days == 6  # 31. März to 5. April inclusive

        # Extra keys
        assert trip.extra["vehicle"] == "Honda CB 500X"

        # URL
        assert trip.url == "trips/2026-test-tour/"

    def test_trip_no_route(self, tmp_path: Path):
        trip_dir = tmp_path / "no-route"
        trip_dir.mkdir()
        (trip_dir / "description.md").write_text(
            "+++\ntitle = 'Empty'\n+++\nNothing.", encoding="utf-8"
        )
        trip = load_trip(trip_dir)
        assert trip.route_geojson is None
        assert trip.route_geojson_json == "null"
        assert trip.entries == []

    def test_trip_no_entries(self, data_dir: Path):
        """Trip with route but entries dir removed."""
        trip_dir = data_dir / "trips" / "2026-test-tour"
        import shutil
        shutil.rmtree(trip_dir / "entries")
        trip = load_trip(trip_dir)
        assert trip.entries == []
        assert trip.route_geojson is not None

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
        assert trip.route_geojson is not None
        feat = trip.route_geojson["features"][0]
        assert feat["geometry"]["type"] == "LineString"

    def test_trip_duration_calculation(self, tmp_path: Path):
        """Test that duration_days is calculated correctly."""
        trip_dir = tmp_path / "duration-test"
        trip_dir.mkdir()
        (trip_dir / "description.md").write_text(
            "+++\ntitle = 'Duration Test'\n+++\n", encoding="utf-8"
        )
        entries_dir = trip_dir / "entries"
        entries_dir.mkdir()
        
        # Create 3 entries spanning 5 days (inclusive)
        # 2026-05-01, 2026-05-03, 2026-05-05 → 5 days between first and last
        for i, day in enumerate(["01", "03", "05"], 1):
            entry_dir = entries_dir / f"2026-05-{day}-day{i}"
            entry_dir.mkdir()
            (entry_dir / "text.md").write_text(
                f"+++\ndate = 2026-05-{day}\n+++\nDay {i}", encoding="utf-8"
            )
        
        trip = load_trip(trip_dir)
        assert trip.start_date == "2026-05-01"
        assert trip.duration_days == 5


# ── load_all_trips ──────────────────────────────────────────────────────────

class TestLoadAllTrips:
    def test_loads_trips(self, data_dir: Path):
        trips = load_all_trips(data_dir)
        assert len(trips) == 1
        assert trips[0].id == "2026-test-tour"

    def test_empty_data_dir(self, tmp_path: Path):
        data = tmp_path / "empty"
        data.mkdir()
        trips = load_all_trips(data)
        assert trips == []

    def test_loads_example_data(self, example_data_dir: Path):
        trips = load_all_trips(example_data_dir)
        assert len(trips) == 1
        assert trips[0].title == "Example Europe Trip"
        assert len(trips[0].entries) == 2

    def test_load_all_trips_excludes_videos_when_requested(self, data_dir: Path):
        trips = load_all_trips(data_dir, skip_videos=True)
        assert len(trips) == 1
        media = trips[0].entries[0].media
        assert all(item.type != "video" for item in media)

    def test_trips_sorted_by_start_date_descending(self, tmp_path: Path):
        """Test that trips are sorted by start_date in descending order (newest first)."""
        data_dir = tmp_path / "trips"
        data_dir.mkdir()
        
        # Create 3 trips with different start dates (unsorted order)
        for trip_name, start_date, end_date in [
            ("trip-b", "2026-06-01", "2026-06-05"),
            ("trip-a", "2026-07-01", "2026-07-05"),  # Newest
            ("trip-c", "2026-05-01", "2026-05-05"),  # Oldest
        ]:
            trip_dir = data_dir / trip_name
            trip_dir.mkdir()
            (trip_dir / "description.md").write_text(
                f"+++\ntitle = '{trip_name.title()}'\n+++\n", encoding="utf-8"
            )
            entries_dir = trip_dir / "entries"
            entries_dir.mkdir()
            
            for i, date in enumerate([start_date, end_date], 1):
                entry_dir = entries_dir / f"{date}-entry{i}"
                entry_dir.mkdir()
                (entry_dir / "text.md").write_text(
                    f"+++\ndate = {date}\n+++\nEntry {i}", encoding="utf-8"
                )
        
        trips = load_all_trips(tmp_path)
        assert len(trips) == 3
        
        # Verify descending order (newest first)
        assert trips[0].id == "trip-a"
        assert trips[0].start_date == "2026-07-01"
        assert trips[1].id == "trip-b"
        assert trips[1].start_date == "2026-06-01"
        assert trips[2].id == "trip-c"
        assert trips[2].start_date == "2026-05-01"


class TestCountryFlags:
    def test_country_to_flag_with_name(self):
        assert country_to_flag("Germany") == "🇩🇪"

    def test_country_to_flag_with_iso_code(self):
        assert country_to_flag("se") == "🇸🇪"

    def test_country_to_flag_unknown(self):
        assert country_to_flag("Atlantis") == ""
