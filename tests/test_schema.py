"""Tests for echotrail_gen.schema — data loading layer."""

from __future__ import annotations

from pathlib import Path

from echotrail_gen.schema import load_all_trips, load_entry, load_trip


class TestLoadAllTrips:
    """Tests for load_all_trips()."""

    def test_loads_example_data(self, example_data_dir: Path) -> None:
        trips = load_all_trips(example_data_dir)
        assert len(trips) == 1

    def test_empty_directory(self, tmp_path: Path) -> None:
        trips = load_all_trips(tmp_path)
        assert trips == []

    def test_missing_directory(self, tmp_path: Path) -> None:
        trips = load_all_trips(tmp_path / "nonexistent")
        assert trips == []


class TestLoadTrip:
    """Tests for load_trip()."""

    def test_loads_example_trip(self, example_data_dir: Path) -> None:
        trip_dir = example_data_dir / "trips" / "example-europe-trip"
        trip = load_trip(trip_dir)

        assert trip["id"] == "example-europe-trip"
        assert trip["title"] == "Example Europe Trip"
        assert trip["odometer_km"] == "3.240"
        assert trip["route_geojson"] is not None
        assert trip["route_geojson"]["type"] == "FeatureCollection"
        assert trip["url"] == "trips/example-europe-trip/"

    def test_trip_has_entries(self, example_data_dir: Path) -> None:
        trip_dir = example_data_dir / "trips" / "example-europe-trip"
        trip = load_trip(trip_dir)

        assert len(trip["entries"]) == 2
        entry_ids = [e["id"] for e in trip["entries"]]
        assert "2026-03-31-berlin" in entry_ids
        assert "2026-04-05-prague" in entry_ids

    def test_minimal_trip(self, tmp_path: Path) -> None:
        """A trip with only a title.txt should load without errors."""
        trip_dir = tmp_path / "trips" / "minimal"
        trip_dir.mkdir(parents=True)
        (trip_dir / "title.txt").write_text("Minimal Trip")

        trip = load_trip(trip_dir)
        assert trip["title"] == "Minimal Trip"
        assert trip["entries"] == []
        assert trip["route_geojson"] is None
        assert trip["cover"] is None

    def test_trip_without_title_uses_dirname(self, tmp_path: Path) -> None:
        trip_dir = tmp_path / "trips" / "my-trip"
        trip_dir.mkdir(parents=True)

        trip = load_trip(trip_dir)
        assert trip["title"] == "my-trip"


class TestLoadEntry:
    """Tests for load_entry()."""

    def test_loads_berlin_entry(self, example_data_dir: Path) -> None:
        entry_dir = (
            example_data_dir
            / "trips"
            / "example-europe-trip"
            / "entries"
            / "2026-03-31-berlin"
        )
        entry = load_entry(entry_dir, "example-europe-trip")

        assert entry["id"] == "2026-03-31-berlin"
        assert entry["trip_id"] == "example-europe-trip"
        assert entry["date"] == "2026-03-31"
        assert entry["country"] == "Germany"
        assert entry["weather"] == "Cloudy, light wind"
        assert entry["temperature_c"] == "9"
        assert entry["point_geojson"] is not None
        assert "Berlin" in entry["text_md"]

    def test_minimal_entry(self, tmp_path: Path) -> None:
        """An empty entry directory should load without errors."""
        entry_dir = tmp_path / "entries" / "empty"
        entry_dir.mkdir(parents=True)

        entry = load_entry(entry_dir, "trip-1")
        assert entry["id"] == "empty"
        assert entry["date"] == ""
        assert entry["country"] == ""
        assert entry["point_geojson"] is None
        assert entry["media"] == []
