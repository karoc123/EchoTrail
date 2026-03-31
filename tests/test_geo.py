"""Tests for echotrail_gen.geo – GeoJSON loading and GPX conversion."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from echotrail_gen.geo import load_geojson, gpx_to_geojson
from echotrail_gen.exceptions import GeoProcessingError


# ── load_geojson ────────────────────────────────────────────────────────────

class TestLoadGeojson:
    def test_valid_file(self, tmp_path: Path):
        fc = {"type": "FeatureCollection", "features": []}
        p = tmp_path / "route.geojson"
        p.write_text(json.dumps(fc), encoding="utf-8")
        result = load_geojson(p)
        assert result["type"] == "FeatureCollection"

    def test_non_object_raises(self, tmp_path: Path):
        p = tmp_path / "bad.geojson"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="Expected a JSON object"):
            load_geojson(p)

    def test_loads_example_route(self, example_data_dir: Path):
        route_path = (
            example_data_dir / "trips" / "example-europe-trip" / "route.geojson"
        )
        result = load_geojson(route_path)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1


# ── gpx_to_geojson ─────────────────────────────────────────────────────────

class TestGpxToGeojson:
    def test_track_conversion(self, tmp_path: Path):
        gpx = textwrap.dedent("""\
            <?xml version="1.0"?>
            <gpx version="1.1">
              <trk>
                <name>Test Route</name>
                <trkseg>
                  <trkpt lat="52.52" lon="13.405"><ele>34</ele></trkpt>
                  <trkpt lat="50.07" lon="14.44"><ele>200</ele></trkpt>
                </trkseg>
              </trk>
            </gpx>
        """)
        p = tmp_path / "route.gpx"
        p.write_text(gpx, encoding="utf-8")
        result = gpx_to_geojson(p)

        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1
        feat = result["features"][0]
        assert feat["geometry"]["type"] == "LineString"
        assert feat["properties"]["name"] == "Test Route"
        # Coordinates include elevation
        assert feat["geometry"]["coordinates"][0] == [13.405, 52.52, 34.0]

    def test_waypoints(self, tmp_path: Path):
        gpx = textwrap.dedent("""\
            <?xml version="1.0"?>
            <gpx version="1.1">
              <wpt lat="48.2" lon="16.37">
                <name>Vienna</name>
                <desc>Capital</desc>
              </wpt>
            </gpx>
        """)
        p = tmp_path / "wpts.gpx"
        p.write_text(gpx, encoding="utf-8")
        result = gpx_to_geojson(p)

        assert len(result["features"]) == 1
        feat = result["features"][0]
        assert feat["geometry"]["type"] == "Point"
        assert feat["geometry"]["coordinates"] == [16.37, 48.2]
        assert feat["properties"]["name"] == "Vienna"
        assert feat["properties"]["description"] == "Capital"

    def test_gpx_with_namespace(self, tmp_path: Path):
        gpx = textwrap.dedent("""\
            <?xml version="1.0"?>
            <gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
              <trk>
                <trkseg>
                  <trkpt lat="51.0" lon="10.0"/>
                </trkseg>
              </trk>
            </gpx>
        """)
        p = tmp_path / "ns.gpx"
        p.write_text(gpx, encoding="utf-8")
        result = gpx_to_geojson(p)

        assert len(result["features"]) == 1
        coords = result["features"][0]["geometry"]["coordinates"]
        assert coords == [[10.0, 51.0]]

    def test_empty_gpx(self, tmp_path: Path):
        gpx = '<?xml version="1.0"?><gpx version="1.1"></gpx>'
        p = tmp_path / "empty.gpx"
        p.write_text(gpx, encoding="utf-8")
        result = gpx_to_geojson(p)
        assert result["features"] == []

    def test_invalid_xml_raises_geo_processing_error(self, tmp_path: Path):
        """Test that malformed XML raises GeoProcessingError."""
        p = tmp_path / "bad.gpx"
        p.write_text("<gpx><unclosed>", encoding="utf-8")
        with pytest.raises(GeoProcessingError, match="Invalid GPX XML"):
            gpx_to_geojson(p)

    def test_missing_lat_attribute_raises_error(self, tmp_path: Path):
        """Test that missing lat attribute raises GeoProcessingError."""
        gpx = textwrap.dedent("""\
            <?xml version="1.0"?>
            <gpx version="1.1">
              <trk>
                <trkseg>
                  <trkpt lon="10.0"/>
                </trkseg>
              </trk>
            </gpx>
        """)
        p = tmp_path / "no_lat.gpx"
        p.write_text(gpx, encoding="utf-8")
        with pytest.raises(GeoProcessingError, match="Invalid track point"):
            gpx_to_geojson(p)

    def test_invalid_latitude_range_raises_error(self, tmp_path: Path):
        """Test that latitude outside valid range raises GeoProcessingError."""
        gpx = textwrap.dedent("""\
            <?xml version="1.0"?>
            <gpx version="1.1">
              <trk>
                <trkseg>
                  <trkpt lat="999" lon="10.0"/>
                </trkseg>
              </trk>
            </gpx>
        """)
        p = tmp_path / "bad_lat.gpx"
        p.write_text(gpx, encoding="utf-8")
        with pytest.raises(GeoProcessingError, match="Invalid latitude.*must be between -90 and 90"):
            gpx_to_geojson(p)

    def test_invalid_longitude_range_raises_error(self, tmp_path: Path):
        """Test that longitude outside valid range raises GeoProcessingError."""
        gpx = textwrap.dedent("""\
            <?xml version="1.0"?>
            <gpx version="1.1">
              <wpt lat="50.0" lon="999">
                <name>Invalid</name>
              </wpt>
            </gpx>
        """)
        p = tmp_path / "bad_lon.gpx"
        p.write_text(gpx, encoding="utf-8")
        with pytest.raises(GeoProcessingError, match="Invalid waypoint longitude.*must be between -180 and 180"):
            gpx_to_geojson(p)
