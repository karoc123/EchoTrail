"""Tests for echotrail_gen.builder — build pipeline."""

from __future__ import annotations

from pathlib import Path

from echotrail_gen.builder import (
    _bundled_assets,
    _bundled_templates,
    _markdown_to_html,
    build,
)


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


class TestMarkdownToHTML:
    """Basic smoke-tests for the built-in Markdown renderer."""

    def test_paragraph(self) -> None:
        assert "<p>" in _markdown_to_html("Hello world")

    def test_heading(self) -> None:
        html = _markdown_to_html("# Title")
        assert "<h1>" in html
        assert "Title" in html

    def test_bold(self) -> None:
        html = _markdown_to_html("**bold**")
        assert "<strong>bold</strong>" in html or "<b>bold</b>" in html


class TestBuild:
    """Integration tests running a full build against example data."""

    def test_build_with_defaults(self, example_data_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "dist"
        build(data_dir=str(example_data_dir), output_dir=str(out))

        assert (out / "index.html").is_file()
        assert (out / "assets" / "css" / "style.css").is_file()
        assert (out / "trips" / "example-europe-trip" / "index.html").is_file()
        assert (
            out
            / "trips"
            / "example-europe-trip"
            / "entries"
            / "2026-03-31-berlin"
            / "index.html"
        ).is_file()
        assert (
            out
            / "trips"
            / "example-europe-trip"
            / "entries"
            / "2026-04-05-prague"
            / "index.html"
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
        custom_tpl = tmp_path / "custom_templates"
        custom_tpl.mkdir()

        # Copy bundled templates as a starting point, modify one
        import shutil

        for f in _bundled_templates().iterdir():
            shutil.copy2(f, custom_tpl / f.name)

        # Modify index.html to include a marker
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

    def test_build_empty_data(self, tmp_path: Path) -> None:
        """Build with no trips should produce an index page without errors."""
        data = tmp_path / "empty_data" / "trips"
        data.mkdir(parents=True)

        out = tmp_path / "dist"
        build(data_dir=str(data.parent), output_dir=str(out))

        assert (out / "index.html").is_file()
        index_html = (out / "index.html").read_text()
        assert "No trips found" in index_html

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
