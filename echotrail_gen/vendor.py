"""Download vendored third-party assets (Leaflet, GLightbox) into assets/vendor/."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

from echotrail_gen.exceptions import VendorFetchError

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

# GLightbox 3.3.0
GLIGHTBOX_VERSION = "3.3.0"
GLIGHTBOX_BASE_URL = f"https://cdn.jsdelivr.net/npm/glightbox@{GLIGHTBOX_VERSION}/dist"

GLIGHTBOX_FILES = [
    "js/glightbox.min.js",
    "css/glightbox.min.css",
]

# Network timeout for vendor downloads (in seconds).
# 30 seconds is generous for small JS/CSS files even on slow connections.
DOWNLOAD_TIMEOUT = 30


def _download_files(base_url: str, files: list[str], vendor_dir: Path) -> None:
    """Download *files* from *base_url* into *vendor_dir*, skipping existing."""
    for rel_path in files:
        dest = vendor_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 0:
            log.info("  skip (exists): %s", dest)
            continue
        url = f"{base_url}/{rel_path}"
        log.info("  fetching: %s → %s", url, dest)
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as resp:
                dest.write_bytes(resp.read())
            log.info("  ok: %s (%d bytes)", dest.name, dest.stat().st_size)
        except Exception as exc:
            log.error("  FAILED %s: %s", url, exc)
            raise VendorFetchError(url, str(exc)) from exc


def fetch_vendor(assets_dir: str = "assets") -> None:
    """Download Leaflet and GLightbox into ``<assets_dir>/vendor/``.

    Safe to re-run: existing files are skipped unless they are empty.
    """
    # --- Leaflet ---
    leaflet_dir = Path(assets_dir) / "vendor" / "leaflet"
    leaflet_dir.mkdir(parents=True, exist_ok=True)
    (leaflet_dir / "images").mkdir(exist_ok=True)
    _download_files(LEAFLET_BASE_URL, LEAFLET_FILES, leaflet_dir)
    print(f"Leaflet {LEAFLET_VERSION} vendored successfully into {leaflet_dir}.")

    # --- GLightbox ---
    glightbox_dir = Path(assets_dir) / "vendor" / "glightbox"
    glightbox_dir.mkdir(parents=True, exist_ok=True)
    _download_files(GLIGHTBOX_BASE_URL, GLIGHTBOX_FILES, glightbox_dir)
    print(f"GLightbox {GLIGHTBOX_VERSION} vendored successfully into {glightbox_dir}.")
