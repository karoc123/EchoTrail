"""Tests for echotrail_gen.cli – argument parsing and command dispatch."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from echotrail_gen.cli import main


class TestCli:
    def test_build_defaults(self, monkeypatch):
        """'build' with no extra args uses bundled defaults (None)."""
        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("echotrail_gen.cli.build", fake_build)
        main(["build"])

        assert captured["data_dir"] == "data"
        assert captured["output_dir"] == "dist"
        assert captured["templates_dir"] is None
        assert captured["assets_dir"] is None
        assert captured["fetch_leaflet"] is False
        assert captured["skip_videos"] is False

    def test_build_custom_dirs(self, monkeypatch):
        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("echotrail_gen.cli.build", fake_build)
        main(["build", "--data", "my_data", "--output", "out", "--templates", "tpl", "--assets", "res"])

        assert captured["data_dir"] == "my_data"
        assert captured["output_dir"] == "out"
        assert captured["templates_dir"] == "tpl"
        assert captured["assets_dir"] == "res"

    def test_build_fetch_vendor_flag(self, monkeypatch):
        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("echotrail_gen.cli.build", fake_build)
        main(["build", "--fetch-vendor"])

        assert captured["fetch_leaflet"] is True

    def test_build_exclude_videos_flag(self, monkeypatch):
        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("echotrail_gen.cli.build", fake_build)
        main(["build", "--exclude-videos"])

        assert captured["skip_videos"] is True

    def test_fetch_vendor_defaults(self, monkeypatch):
        captured = {}

        def fake_fetch(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("echotrail_gen.cli.fetch_vendor", fake_fetch)
        main(["fetch-vendor"])

        assert captured["assets_dir"] == "assets"

    def test_no_command_exits(self):
        with pytest.raises(SystemExit):
            main([])

    def test_unknown_command_exits(self):
        with pytest.raises(SystemExit):
            main(["unknown"])


class TestCLIEntryPoint:
    """Verify the package can be invoked as ``python -m echotrail_gen``."""

    def test_module_invocation(self, example_data_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "dist"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "echotrail_gen",
                "build",
                "--data",
                str(example_data_dir),
                "--output",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert (out / "index.html").is_file()
