"""Download vendored third-party assets (Leaflet) into assets/vendor/."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

# Leaflet 1.9.4 — update the version constant to upgrade
LEAFLET_VERSION = "1.9.4"
LEAFLET_BASE_URL = f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist"

LEAFLET_FILES = [
    "leaflet.js",
    "leaflet.css",
    "images/layers.png",
    "images/layers-2x.png",
    "images/marker-icon.png",
    "images/marker-icon-2x.png",
    "images/marker-shadow.png",
]


def fetch_vendor(assets_dir: str = "assets") -> None:
    """Download Leaflet into ``<assets_dir>/vendor/leaflet/``.

    Safe to re-run: existing files are skipped unless they are empty.
    """
    vendor_dir = Path(assets_dir) / "vendor" / "leaflet"
    vendor_dir.mkdir(parents=True, exist_ok=True)
    (vendor_dir / "images").mkdir(exist_ok=True)

    for rel_path in LEAFLET_FILES:
        dest = vendor_dir / rel_path
        if dest.exists() and dest.stat().st_size > 0:
            log.info("  skip (exists): %s", dest)
            continue
        url = f"{LEAFLET_BASE_URL}/{rel_path}"
        log.info("  fetching: %s → %s", url, dest)
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                dest.write_bytes(resp.read())
            log.info("  ok: %s (%d bytes)", dest.name, dest.stat().st_size)
        except Exception as exc:
            log.error("  FAILED %s: %s", url, exc)
            raise SystemExit(
                f"\nCould not download {url}\n"
                "Check your internet connection and try again.\n"
                f"Error: {exc}"
            ) from exc

    print(
        f"Leaflet {LEAFLET_VERSION} vendored successfully into {vendor_dir}."
    )
