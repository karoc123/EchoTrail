"""Tests for echotrail_gen.builder – Markdown rendering, bundled paths, and full build integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from echotrail_gen.builder import build, _markdown_to_html, _bundled_templates, _bundled_assets, BuildResult


# ── Bundled paths ───────────────────────────────────────────────────────────

class TestBundledPaths:
    """The bundled template and asset paths must exist inside the package."""

    def test_bundled_templates_exist(self) -> None:
        tpl = _bundled_templates()
        assert tpl.is_dir()
        assert (tpl / "base.html").is_file()
        assert (tpl / "index.html").is_file()
        assert (tpl / "trip.html").is_file()
        assert (tpl / "entry.html").is_file()

    def test_bundled_assets_exist(self) -> None:
        assets = _bundled_assets()
        assert assets.is_dir()
        assert (assets / "css" / "style.css").is_file()


# ── Markdown rendering ─────────────────────────────────────────────────────

class TestMarkdownToHtml:
    def test_heading(self):
        result = str(_markdown_to_html("# Hello World"))
        assert "<h1>Hello World</h1>" in result

    def test_bold(self):
        result = str(_markdown_to_html("This is **bold**."))
        assert "<strong>bold</strong>" in result

    def test_paragraph(self):
        result = str(_markdown_to_html("Paragraph one.\n\nParagraph two."))
        assert "<p>Paragraph one.</p>" in result
        assert "<p>Paragraph two.</p>" in result

    def test_unordered_list(self):
        result = str(_markdown_to_html("- One\n- Two"))
        assert "<li>One</li>" in result
        assert "<li>Two</li>" in result

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
        build(
            data_dir=str(data_dir),
            output_dir=str(self.dist),
            templates_dir=str(templates_dir),
            assets_dir=str(assets_dir),
        )

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
            self.dist / "trips" / "2026-test-tour" / "entries" / "2026-04-05-prague" / "index.html"
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
        assert "2 entries" in html

    # -- trip.html --

    def test_trip_contains_title(self):
        html = self._read("trips", "2026-test-tour", "index.html")
        assert "<h1>Test-Tour 2026</h1>" in html

    def test_trip_contains_route_geojson(self):
        html = self._read("trips", "2026-test-tour", "index.html")
        assert "LineString" in html
        assert "Test Route" in html

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
        assert "<h1>Test-Tour 2026</h1>" in html or "test trip" in html

    # -- entry.html (Berlin) --

    def test_entry_berlin_contains_date_and_country(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "2026-03-31" in html
        assert "Germany" in html

    def test_entry_berlin_contains_weather(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "Cloudy" in html

    def test_entry_berlin_contains_rendered_markdown(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "<h1>Departure from Berlin</h1>" in html
        assert "<strong>Fantastic</strong>" in html

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
        # Thumbnails in the gallery grid link to full images via GLightbox
        assert 'class="glightbox' in html
        assert 'href="media/foto1.jpg"' in html
        assert 'src="media/thumb_foto1.jpg"' in html
        assert "<video" in html
        assert "clip.mp4" in html

    def test_entry_berlin_media_files_copied(self):
        media_dir = (
            self.dist / "trips" / "2026-test-tour" / "entries" / "2026-03-31-berlin" / "media"
        )
        assert (media_dir / "foto1.jpg").exists()
        assert (media_dir / "thumb_foto1.jpg").exists()
        assert (media_dir / "clip.mp4").exists()

    # -- Layout order: gallery → text → map --

    def test_entry_layout_order(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        gallery_pos = html.index("gallery-grid")
        text_pos = html.index("entry-text")
        map_pos = html.index("entry-map")
        assert gallery_pos < text_pos < map_pos

    # -- entry.html (Prague – minimal) --

    def test_entry_prague_no_media_section(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-04-05-prague", "index.html"
        )
        assert "Prague in the Morning Light" in html
        assert "gallery-grid" not in html

    # -- Breadcrumb navigation --

    def test_entry_has_breadcrumb(self):
        html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        assert "All Trips" in html
        assert "Test-Tour 2026" in html

    def test_entry_prev_next_navigation(self):
        berlin_html = self._read(
            "trips", "2026-test-tour", "entries", "2026-03-31-berlin", "index.html"
        )
        prague_html = self._read(
            "trips", "2026-test-tour", "entries", "2026-04-05-prague", "index.html"
        )

        assert 'href="../2026-04-05-prague/index.html"' in berlin_html
        assert "Prague in the Morning Light →" in berlin_html
        assert 'href="../2026-03-31-berlin/index.html"' not in berlin_html

        assert 'href="../2026-03-31-berlin/index.html"' in prague_html
        assert "← Departure from Berlin" in prague_html
        assert 'href="../2026-04-05-prague/index.html"' not in prague_html

    # -- Assets --

    def test_assets_copied(self):
        assert (self.dist / "assets" / "css" / "style.css").exists()
        assert (self.dist / "assets" / "vendor" / "leaflet" / "leaflet.js").exists()


# ── Build with bundled defaults ─────────────────────────────────────────────

class TestBuildWithBundledDefaults:
    """Build using bundled templates/assets (no explicit --templates/--assets)."""

    def test_build_with_bundled_defaults(self, example_data_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "dist"
        build(data_dir=str(example_data_dir), output_dir=str(out))

        assert (out / "index.html").is_file()
        assert (out / "assets" / "css" / "style.css").is_file()
        assert (out / "trips" / "example-europe-trip" / "index.html").is_file()
        assert (
            out / "trips" / "example-europe-trip" / "entries" / "2026-03-31-berlin" / "index.html"
        ).is_file()

    def test_output_is_english(self, example_data_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "dist"
        build(data_dir=str(example_data_dir), output_dir=str(out))

        index_html = (out / "index.html").read_text()
        assert "All Trips" in index_html
        assert 'lang="en"' in index_html

    def test_build_with_custom_templates(
        self, example_data_dir: Path, tmp_path: Path
    ) -> None:
        """When custom templates are given they should be used instead."""
        import shutil

        custom_tpl = tmp_path / "custom_templates"
        custom_tpl.mkdir()
        for f in _bundled_templates().iterdir():
            shutil.copy2(f, custom_tpl / f.name)

        idx = custom_tpl / "index.html"
        content = idx.read_text()
        content = content.replace("All Trips", "My Custom Trips")
        idx.write_text(content)

        out = tmp_path / "dist"
        build(
            data_dir=str(example_data_dir),
            output_dir=str(out),
            templates_dir=str(custom_tpl),
        )

        index_html = (out / "index.html").read_text()
        assert "My Custom Trips" in index_html

    def test_custom_assets_overlay_preserves_bundled_css(
        self, example_data_dir: Path, tmp_path: Path
    ) -> None:
        """--assets should overlay on top of bundled defaults, not replace them."""
        custom_assets = tmp_path / "my_assets" / "vendor" / "leaflet"
        custom_assets.mkdir(parents=True)
        (custom_assets / "leaflet.js").write_text("/* custom */", encoding="utf-8")

        out = tmp_path / "dist"
        build(
            data_dir=str(example_data_dir),
            output_dir=str(out),
            assets_dir=str(tmp_path / "my_assets"),
        )

        # Bundled CSS must still be present
        assert (out / "assets" / "css" / "style.css").is_file()
        # Custom vendor file should have overridden the bundled stub
        assert (out / "assets" / "vendor" / "leaflet" / "leaflet.js").read_text() == "/* custom */"


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
        assert "All Trips" in html
        assert "No trips found" in html

    def test_trip_without_route_renders(
        self, tmp_path: Path, templates_dir: Path, assets_dir: Path
    ):
        data = tmp_path / "data" / "trips" / "no-route"
        data.mkdir(parents=True)
        (data / "description.md").write_text(
            "+++\ntitle = 'No Route'\n+++\nNo route.", encoding="utf-8"
        )
        dist = tmp_path / "dist"

        build(
            data_dir=str(tmp_path / "data"),
            output_dir=str(dist),
            templates_dir=str(templates_dir),
            assets_dir=str(assets_dir),
        )

        html = (dist / "trips" / "no-route" / "index.html").read_text(encoding="utf-8")
        assert "No Route" in html
        assert "null" in html

    def test_build_cleans_output(
        self, example_data_dir: Path, tmp_path: Path
    ) -> None:
        """Consecutive builds should clean the output directory."""
        out = tmp_path / "dist"
        stale = out / "stale.html"
        out.mkdir(parents=True)
        stale.write_text("old")

        build(data_dir=str(example_data_dir), output_dir=str(out))
        assert not stale.exists()


# ── BuildResult ─────────────────────────────────────────────────────────────

class TestBuildResult:
    """Test BuildResult dataclass."""

    def test_build_returns_result(self, example_data_dir: Path, tmp_path: Path) -> None:
        """Test that build() returns a BuildResult."""
        out = tmp_path / "dist"
        result = build(data_dir=str(example_data_dir), output_dir=str(out))

        assert isinstance(result, BuildResult)
        assert result.trips_count == 1
        assert result.entries_count == 2
        assert result.output_path == out
        assert result.warnings == []

    def test_build_result_str(self, example_data_dir: Path, tmp_path: Path) -> None:
        """Test BuildResult string representation."""
        out = tmp_path / "dist"
        result = build(data_dir=str(example_data_dir), output_dir=str(out))

        result_str = str(result)
        assert str(out) in result_str
        assert "1 trip(s)" in result_str
        assert "2 entrie(s)" in result_str

    def test_empty_build_result(self, tmp_path: Path, templates_dir: Path, assets_dir: Path) -> None:
        """Test BuildResult for empty data dir."""
        data = tmp_path / "data"
        (data / "trips").mkdir(parents=True)
        out = tmp_path / "dist"

        result = build(
            data_dir=str(data),
            output_dir=str(out),
            templates_dir=str(templates_dir),
            assets_dir=str(assets_dir),
        )

        assert result.trips_count == 0
        assert result.entries_count == 0
