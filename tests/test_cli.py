"""Tests for echotrail_gen.cli – argument parsing and command dispatch."""

from __future__ import annotations

import pytest

from echotrail_gen.cli import main


class TestCli:
    def test_build_defaults(self, monkeypatch):
        """'build' with no extra args uses default directories."""
        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("echotrail_gen.cli.build", fake_build)
        main(["build"])

        assert captured["data_dir"] == "data"
        assert captured["output_dir"] == "dist"
        assert captured["templates_dir"] == "templates"
        assert captured["assets_dir"] == "assets"

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
