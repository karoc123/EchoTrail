"""Tests for echotrail_gen.cli — command-line interface."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from echotrail_gen.cli import main


class TestCLIParsing:
    """Verify the CLI parses arguments correctly."""

    def test_build_defaults(self, example_data_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "dist"
        main(["build", "--data", str(example_data_dir), "--output", str(out)])
        assert (out / "index.html").is_file()

    def test_build_custom_templates(
        self, example_data_dir: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "dist"
        tpl = str(_bundled_templates())
        main([
            "build",
            "--data", str(example_data_dir),
            "--output", str(out),
            "--templates", tpl,
        ])
        assert (out / "index.html").is_file()

    def test_missing_command_exits(self) -> None:
        with pytest.raises(SystemExit):
            main([])

    def test_build_missing_templates_dir_exits(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            main([
                "build",
                "--data", str(tmp_path),
                "--output", str(tmp_path / "out"),
                "--templates", str(tmp_path / "nonexistent"),
            ])


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


def _bundled_templates() -> Path:
    from echotrail_gen.builder import _bundled_templates

    return _bundled_templates()
