"""Shared test fixtures for EchoTrail tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DATA = REPO_ROOT / "example_data"


@pytest.fixture()
def example_data_dir() -> Path:
    """Return the path to the shipped example data."""
    return EXAMPLE_DATA


@pytest.fixture()
def output_dir(tmp_path: Path) -> Path:
    """Return a fresh temporary output directory."""
    out = tmp_path / "dist"
    out.mkdir()
    return out
