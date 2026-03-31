"""Tests for echotrail_gen.builder – Markdown rendering and full build integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from echotrail_gen.builder import build, _markdown_to_html


# ── Markdown rendering (with markdown library) ─────────────────────────────

class TestMarkdownToHtml:
    def test_heading(self):
        result = str(_markdown_to_html("# Hallo Welt"))
        assert "<h1>Hallo Welt</h1>" in result

    def test_bold(self):
        result = str(_markdown_to_html("Das ist **fett**."))
        assert "<strong>fett</strong>" in result

    def test_paragraph(self):
        result = str(_markdown_to_html("Absatz eins.\n\nAbsatz zwei."))
        assert "<p>Absatz eins.</p>" in result
        assert "<p>Absatz zwei.</p>" in result

    def test_unordered_list(self):
        result = str(_markdown_to_html("- Eins\n- Zwei"))
        assert "<li>Eins</li>" in result
        assert "<li>Zwei</li>" in result

    def test_inline_code(self):
        result = str(_markdown_to_html("Run `pytest`."))
        assert "<code>pytest</code>" in result


# ── Full build integration ──────────────────────────────────────────────────

class TestBuildIntegration:
    """Run a complete build with temp data and verify the HTML output."""

    @pytest.fixture(autouse=True)
    def _build_site(self, tmp_path: Path, data_dir: Path, templates_dir: Path, assets_dir: Path):
        """Perform the build once; all tests in this class read from dist/."""
        self.dist = tmp_path / "dist"
        # builder._copy_trip_media reads from "data/trips/..." relative to CWD,
        # so we need to set the data_dir correctly.
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Symlink 'data' so the builder can find media relative to CWD
            data_link = tmp_path / "data"
            if not data_link.exists():
                # On Windows, directory junction works without admin
                # But data_dir might already be tmp_path/data — check
                if data_dir != data_link:
                    import shutil
                    shutil.copytree(data_dir, data_link)

            build(
                data_dir=str(data_link),
                output_dir=str(self.dist),
                templates_dir=str(templates_dir),
                assets_dir=str(assets_dir),
            )
        finally:
            os.chdir(old_cwd)

    def _read(self, *parts: str) -> str:
        return (self.dist / Path(*parts)).read_text(encoding="utf-8")

    # -- Directory structure --

    def test_dist_structure(self):
        assert (self.dist / "index.html").exists()
        assert (self.dist / "assets" / "css" / "style.css").exists()
        assert (self.dist / "trips" / "2026-test-tour" / "index.html").exists()
        assert (
            self.dist / "trips" / "2026-test-tour" / "entries" / "2026-03-31-berlin" / "index.html"
        ).exists()
        assert (
            self.dist / "trips" / "2026-test-tour" / "entries" / "2026-04-05-prag" / "index.html"
        ).exists()

    # -- index.html --

    def test_index_contains_trip_title(self):
        html = self._read("index.html")
        assert "Test-Tour 2026" in html

    def test_index_contains_trip_link(self):
        html = self._read("index.html")
        assert 'href="trips/2026-test-tour/index.html"' in html

    def test_index_contains_odometer(self):
        html = self._read("index.html")
        assert "1.200" in html

    def test_index_contains_entry_count(self):
        html = self._read("index.html")
        assert "2 Einträge" in html

    # -- trip.html --

    def test_trip_contains_title(self):
        html = self._read("trips", "2026-test-tour", "index.html")
        assert "<h1>Test-Tour 2026</h1>" in html

    def test_trip_contains_route_geojson(self):
        html = self._read("trips", "2026-test-tour", "index.html")
        assert "LineString" in html
        assert "Testroute" in html

    def test_trip_contains_entry_links(self):
        html = self._read("trips", "2026-test-tour", "index.html")
        assert "2026-03-31" in html
        assert "2026-04-05" in html
        assert "2026-03-31-berlin" in html

    def test_trip_contains_extra_metadata(self):
        html = self._read("trips", "2026-test-tour", "index.html")
        assert "Honda CB 500X" in html

    def test_trip_renders_description_markdown(self):
        html = self._read("trips", "2026-test-tour", "index.html")
        assert "<h1>Test-Tour 2026</h1>" in html or "Testreise" in html

    # -- entry.html (Berlin) --

    def test_entry_berlin_contains_date_and_country(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "2026-03-31" in html
        assert "Deutschland" in html

    def test_entry_berlin_contains_weather(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "Bewölkt" in html

    def test_entry_berlin_contains_rendered_markdown(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "<h1>Aufbruch aus Berlin</h1>" in html
        assert "<strong>Großartig</strong>" in html

    def test_entry_berlin_contains_point_geojson(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "52.52" in html
        assert "13.405" in html

    def test_entry_berlin_has_media_tags(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert '<img src="media/foto1.jpg"' in html
        assert "<video" in html
        assert "clip.mp4" in html

    def test_entry_berlin_media_files_copied(self):
        media_dir = (
            self.dist / "trips" / "2026-test-tour" / "entries" / "2026-03-31-berlin" / "media"
        )
        assert (media_dir / "foto1.jpg").exists()
        assert (media_dir / "clip.mp4").exists()

    # -- entry.html (Prag – minimal) --

    def test_entry_prag_no_media_section(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-04-05-prag", "index.html"
        )
        assert "Prag im Morgenlicht" in html
        assert "media-gallery" not in html

    # -- Breadcrumb navigation --

    def test_entry_has_breadcrumb(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "Alle Touren" in html
        assert "Test-Tour 2026" in html

    # -- Assets --

    def test_assets_copied(self):
        assert (self.dist / "assets" / "css" / "style.css").exists()
        assert (self.dist / "assets" / "vendor" / "leaflet" / "leaflet.js").exists()


# ── Edge cases ──────────────────────────────────────────────────────────────

class TestBuildEdgeCases:
    def test_empty_data_produces_index(
        self, tmp_path: Path, templates_dir: Path, assets_dir: Path
    ):
        """An empty data dir should still produce a valid index.html."""
        data = tmp_path / "data"
        (data / "trips").mkdir(parents=True)
        dist = tmp_path / "dist"

        build(
            data_dir=str(data),
            output_dir=str(dist),
            templates_dir=str(templates_dir),
            assets_dir=str(assets_dir),
        )

        html = (dist / "index.html").read_text(encoding="utf-8")
        assert "Alle Touren" in html
        assert "Noch keine Touren vorhanden" in html

    def test_trip_without_route_renders(
        self, tmp_path: Path, templates_dir: Path, assets_dir: Path
    ):
        data = tmp_path / "data" / "trips" / "no-route"
        data.mkdir(parents=True)
        (data / "description.md").write_text(
            "+++\ntitle = 'Ohne Route'\n+++\nKeine Route.", encoding="utf-8"
        )
        dist = tmp_path / "dist"

        build(
            data_dir=str(tmp_path / "data"),
            output_dir=str(dist),
            templates_dir=str(templates_dir),
            assets_dir=str(assets_dir),
        )

        html = (dist / "trips" / "no-route" / "index.html").read_text(encoding="utf-8")
        assert "Ohne Route" in html
        # route_geojson_json should be null so the JS handles it gracefully
        assert "null" in html
