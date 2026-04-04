"""Main build pipeline.

Usage::

    from tracevoyage_gen.builder import build
    build(data_dir="data", output_dir="dist")

Or via the CLI::

    python -m tracevoyage_gen build
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import markdown as md_markdown
from markupsafe import Markup

from tracevoyage_gen.exceptions import TemplateNotFoundError
from tracevoyage_gen.schema import Entry, Trip, load_all_trips
from tracevoyage_gen.images import process_entry_media

log = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parent


class _WarningCollector(logging.Handler):
    """Logging handler that collects WARNING-level messages into a list."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.warnings: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.WARNING:
            self.warnings.append(self.format(record))


def _pluralize(count: int, singular: str, plural: str) -> str:
    """Return *singular* when *count* is 1, otherwise *plural*."""
    return singular if count == 1 else plural


# ---------------------------------------------------------------------------
# Build result
# ---------------------------------------------------------------------------


@dataclass
class BuildResult:
    """Result of a build operation.

    Provides structured feedback about the build process, making it easier
    to test build outcomes and report issues programmatically.
    """

    trips_count: int
    """Number of trips processed."""

    entries_count: int
    """Total number of entries across all trips."""

    output_path: Path
    """Path to the generated output directory."""

    warnings: list[str] = field(default_factory=list)
    """List of non-fatal warnings encountered during build."""

    def __str__(self) -> str:
        """Human-readable summary of build results."""
        lines = [
            f"Build complete → {self.output_path}/",
            f"  {self.trips_count} {_pluralize(self.trips_count, 'trip', 'trips')},"
            f" {self.entries_count} {_pluralize(self.entries_count, 'entry', 'entries')}",
        ]
        if self.warnings:
            lines.append(f"  {len(self.warnings)} warning(s)")
        return "\n".join(lines)


def _bundled_templates() -> Path:
    """Return the path to the bundled default templates."""
    return _PACKAGE_DIR / "default_templates"


def _bundled_assets() -> Path:
    """Return the path to the bundled default assets."""
    return _PACKAGE_DIR / "default_assets"


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def _markdown_to_html(text: str) -> Markup:
    """Render Markdown using the dedicated library."""
    return Markup(md_markdown(text, extensions=["extra"]))


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    """Write content to path atomically to prevent corruption.

    Uses atomic rename to ensure that the file is either fully written
    or not present at all, preventing partial writes on crashes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")

    # Atomic rename (POSIX guarantees atomicity)
    temp_path.replace(path)

    log.debug("  wrote %s", path)


def _copy_assets(
    assets_dir: Path, output_dir: Path, *, custom_assets: Path | None = None
) -> None:
    """Copy bundled + optional custom assets into ``dist/assets/``.

    The bundled default assets are always copied first.  When *custom_assets*
    is given, its contents are overlaid on top so that custom files (e.g.
    pre-fetched vendor libs) win while bundled files like ``css/style.css``
    are preserved.
    """
    dst = output_dir / "assets"
    if dst.exists():
        shutil.rmtree(dst)

    # 1) Always start with the bundled defaults
    shutil.copytree(assets_dir, dst)
    log.info("Copied bundled assets → %s", dst)

    # 2) Overlay custom assets on top (if provided)
    if custom_assets and custom_assets.is_dir():
        shutil.copytree(custom_assets, dst, dirs_exist_ok=True)
        log.info("Overlaid custom assets from %s", custom_assets)


def _check_vendor(assets_dir: Path) -> None:
    """Warn if Leaflet has not been fetched yet."""
    leaflet_js = assets_dir / "vendor" / "leaflet" / "leaflet.js"
    if not leaflet_js.exists() or leaflet_js.stat().st_size == 0:
        log.warning(
            "Leaflet JS not found at %s.\n"
            "Run `python -m tracevoyage_gen fetch-vendor` first, "
            "or maps will not render.",
            leaflet_js,
        )


# ---------------------------------------------------------------------------
# Public build function
# ---------------------------------------------------------------------------


def build(
    data_dir: str = "data",
    output_dir: str = "dist",
    templates_dir: str | None = None,
    assets_dir: str | None = None,
    fetch_leaflet: bool = False,
    skip_videos: bool = False,
) -> BuildResult:
    """Build the complete static site into *output_dir*.

    When *templates_dir* or *assets_dir* are ``None``, the bundled default
    templates / assets shipped with the package are used.  This allows a
    content-only repository to build without carrying its own theme.

    When *fetch_leaflet* is ``True``, Leaflet vendor files are downloaded
    directly into the output assets directory during the build.

    When *skip_videos* is ``True``, video files are excluded from media
    galleries and not copied to the output directory, reducing output size.


    Returns:
        BuildResult: Structured information about the build outcome including
        trip/entry counts and any warnings encountered.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Collect all WARNING-level log messages emitted during the build
    warning_collector = _WarningCollector()
    root_logger = logging.getLogger()
    root_logger.addHandler(warning_collector)

    try:
        data_path = Path(data_dir)
        out_path = Path(output_dir)
        tpl_path = Path(templates_dir) if templates_dir else _bundled_templates()
        custom_assets_path = Path(assets_dir) if assets_dir else None

        # --- Sanity checks ---
        if not tpl_path.is_dir():
            raise TemplateNotFoundError(tpl_path)
        if not fetch_leaflet:
            _check_vendor(custom_assets_path or _bundled_assets())

        # --- Jinja2 environment ---
        env = Environment(
            loader=FileSystemLoader(str(tpl_path)),
            autoescape=select_autoescape(["html"]),
        )
        env.globals["markdown"] = _markdown_to_html

        # --- Load data ---
        log.info("Loading content from %s …", data_path)
        trips = load_all_trips(data_path, skip_videos=skip_videos)
        log.info("Found %d trip(s).", len(trips))

        # --- Clean output directory ---
        if out_path.exists():
            shutil.rmtree(out_path)
        out_path.mkdir(parents=True)

        # --- Copy assets ---
        _copy_assets(_bundled_assets(), out_path, custom_assets=custom_assets_path)

        # --- Optionally fetch vendored Leaflet into output ---
        if fetch_leaflet:
            from tracevoyage_gen.vendor import fetch_vendor

            fetch_vendor(assets_dir=str(out_path / "assets"))

        # --- Render trips index ---
        _render_trips_index(env, trips, out_path)

        # --- Render trip + entry pages ---
        entries_count = 0
        for trip in trips:
            _render_trip_page(env, trip, out_path, skip_videos=skip_videos)
            entries_count += len(trip.entries)
            for index, entry in enumerate(trip.entries):
                prev_entry = trip.entries[index - 1] if index > 0 else None
                next_entry = trip.entries[index + 1] if index + 1 < len(trip.entries) else None
                _render_entry_page(
                    env,
                    trip,
                    entry,
                    out_path,
                    prev_entry=prev_entry,
                    next_entry=next_entry,
                )

        log.info("Build complete → %s/", out_path)

        return BuildResult(
            trips_count=len(trips),
            entries_count=entries_count,
            output_path=out_path,
            warnings=list(warning_collector.warnings),
        )
    finally:
        root_logger.removeHandler(warning_collector)


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------


def _render_trips_index(env: Environment, trips: list[Trip], out_path: Path) -> None:
    tpl = env.get_template("index.html")
    html = tpl.render(trips=trips, page_title="TraceVoyage")
    _write(out_path / "index.html", html)
    log.info("Rendered trips index → index.html")


def _render_trip_page(
    env: Environment,
    trip: Trip,
    out_path: Path,
    *,
    skip_videos: bool = False,
) -> None:
    tpl = env.get_template("trip.html")
    html = tpl.render(trip=trip, page_title=trip.title)
    _write(out_path / "trips" / trip.id / "index.html", html)
    log.info("Rendered trip: %s", trip.id)

    # Copy trip media (cover + entry media)
    _copy_trip_media(trip, out_path, skip_videos=skip_videos)


def _render_entry_page(
    env: Environment,
    trip: Trip,
    entry: Entry,
    out_path: Path,
    *,
    prev_entry: Entry | None = None,
    next_entry: Entry | None = None,
) -> None:
    tpl = env.get_template("entry.html")
    page_title = entry.date or entry.id
    html = tpl.render(
        trip=trip,
        entry=entry,
        prev_entry=prev_entry,
        next_entry=next_entry,
        page_title=page_title,
    )
    dest = out_path / "trips" / trip.id / "entries" / entry.id / "index.html"
    _write(dest, html)
    log.info("  Rendered entry: %s/%s", trip.id, entry.id)


def _copy_trip_media(trip: Trip, out_path: Path, *, skip_videos: bool = False) -> None:
    """Copy trip cover image and all entry media files to dist/."""
    trip_src = trip.source_dir

    # Cover
    if trip.cover:
        src = trip_src / trip.cover
        dst = out_path / "trips" / trip.id / trip.cover
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Entry media (resize images + generate thumbnails)
    for entry in trip.entries:
        entry_src = trip_src / "entries" / entry.id / "media"
        if not entry_src.is_dir():
            continue
        entry_dst = out_path / "trips" / trip.id / "entries" / entry.id / "media"
        if entry_dst.exists():
            shutil.rmtree(entry_dst)
        process_entry_media(entry_src, entry_dst, skip_videos=skip_videos)
