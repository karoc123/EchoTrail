"""Tests for echotrail_gen.geo — GeoJSON loading and GPX conversion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from echotrail_gen.geo import gpx_to_geojson, load_geojson


class TestLoadGeoJSON:
    """Tests for load_geojson()."""

    def test_loads_valid_geojson(self, tmp_path: Path) -> None:
        data = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [13.4, 52.5]},
            "properties": {"name": "Test"},
        }
        p = tmp_path / "point.geojson"
        p.write_text(json.dumps(data))

        result = load_geojson(p)
        assert result["type"] == "Feature"
        assert result["geometry"]["coordinates"] == [13.4, 52.5]

    def test_rejects_non_object(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.geojson"
        p.write_text("[1, 2, 3]")

        with pytest.raises(ValueError, match="Expected a JSON object"):
            load_geojson(p)

    def test_loads_example_route(self, example_data_dir: Path) -> None:
        route_path = (
            example_data_dir / "trips" / "example-europe-trip" / "route.geojson"
        )
        result = load_geojson(route_path)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1


class TestGPXToGeoJSON:
    """Tests for gpx_to_geojson()."""

    def test_converts_track(self, tmp_path: Path) -> None:
        gpx_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Test Track</name>
    <trkseg>
      <trkpt lat="52.52" lon="13.40"><ele>34</ele></trkpt>
      <trkpt lat="50.07" lon="14.44"><ele>200</ele></trkpt>
    </trkseg>
  </trk>
</gpx>
"""
        p = tmp_path / "track.gpx"
        p.write_text(gpx_xml)

        result = gpx_to_geojson(p)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1

        feature = result["features"][0]
        assert feature["geometry"]["type"] == "LineString"
        assert feature["properties"]["name"] == "Test Track"
        assert len(feature["geometry"]["coordinates"]) == 2

    def test_converts_waypoints(self, tmp_path: Path) -> None:
        gpx_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="52.52" lon="13.40">
    <name>Berlin</name>
    <desc>Capital of Germany</desc>
  </wpt>
</gpx>
"""
        p = tmp_path / "wpts.gpx"
        p.write_text(gpx_xml)

        result = gpx_to_geojson(p)
        assert len(result["features"]) == 1

        feature = result["features"][0]
        assert feature["geometry"]["type"] == "Point"
        assert feature["properties"]["name"] == "Berlin"
        assert feature["properties"]["description"] == "Capital of Germany"

    def test_empty_gpx(self, tmp_path: Path) -> None:
        gpx_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
</gpx>
"""
        p = tmp_path / "empty.gpx"
        p.write_text(gpx_xml)

        result = gpx_to_geojson(p)
        assert result["type"] == "FeatureCollection"
        assert result["features"] == []
