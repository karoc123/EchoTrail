"""Main build pipeline.

Usage::

    from echotrail_gen.builder import build
    build(data_dir="data", output_dir="dist", templates_dir="templates", assets_dir="assets")

Or via the CLI::

    python -m echotrail_gen build
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from echotrail_gen.schema import load_all_trips

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Markdown → HTML (minimal, no extra dependency required)
# ---------------------------------------------------------------------------

def _markdown_to_html(text: str) -> str:
    """Convert a small subset of Markdown to HTML.

    Supports: paragraphs, **bold**, *italic*, `code`, headings (# / ##),
    unordered lists (- item), ordered lists (1. item), and line breaks.
    For richer Markdown, install ``markdown`` or ``mistune`` and replace this.
    """
    try:
        import markdown as md_lib  # type: ignore[import]
        return md_lib.markdown(text, extensions=["extra"])
    except ModuleNotFoundError:
        pass

    import re
    lines = text.splitlines()
    html_parts: list[str] = []
    in_ul = False
    in_ol = False
    para_lines: list[str] = []

    def flush_para() -> None:
        nonlocal para_lines
        if para_lines:
            content = " ".join(para_lines).strip()
            if content:
                html_parts.append(f"<p>{content}</p>")
            para_lines = []

    def flush_ul() -> None:
        nonlocal in_ul
        if in_ul:
            html_parts.append("</ul>")
            in_ul = False

    def flush_ol() -> None:
        nonlocal in_ol
        if in_ol:
            html_parts.append("</ol>")
            in_ol = False

    def inline(s: str) -> str:
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        return s

    for line in lines:
        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            flush_para(); flush_ul(); flush_ol()
            level = len(m.group(1))
            html_parts.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            continue

        # Unordered list
        m = re.match(r"^[-*+]\s+(.*)", line)
        if m:
            flush_para(); flush_ol()
            if not in_ul:
                html_parts.append("<ul>")
                in_ul = True
            html_parts.append(f"<li>{inline(m.group(1))}</li>")
            continue

        # Ordered list
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            flush_para(); flush_ul()
            if not in_ol:
                html_parts.append("<ol>")
                in_ol = True
            html_parts.append(f"<li>{inline(m.group(1))}</li>")
            continue

        # Blank line → close lists / paragraph
        if not line.strip():
            flush_para(); flush_ul(); flush_ol()
            continue

        # Normal paragraph line
        flush_ul(); flush_ol()
        para_lines.append(inline(line))

    flush_para(); flush_ul(); flush_ol()
    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log.debug("  wrote %s", path)


def _copy_assets(assets_dir: Path, output_dir: Path) -> None:
    """Copy the entire assets/ tree to dist/assets/."""
    src = assets_dir
    dst = output_dir / "assets"
    if not src.is_dir():
        log.warning("Assets directory not found: %s — skipping.", src)
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    log.info("Copied assets → %s", dst)


def _check_vendor(assets_dir: Path) -> None:
    """Warn if Leaflet has not been fetched yet."""
    leaflet_js = assets_dir / "vendor" / "leaflet" / "leaflet.js"
    if not leaflet_js.exists() or leaflet_js.stat().st_size == 0:
        log.warning(
            "Leaflet JS not found at %s.\n"
            "Run `python -m echotrail_gen fetch-vendor` first, "
            "or maps will not render.",
            leaflet_js,
        )


# ---------------------------------------------------------------------------
# Public build function
# ---------------------------------------------------------------------------


def build(
    data_dir: str = "data",
    output_dir: str = "dist",
    templates_dir: str = "templates",
    assets_dir: str = "assets",
) -> None:
    """Build the complete static site into *output_dir*."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    data_path = Path(data_dir)
    out_path = Path(output_dir)
    tpl_path = Path(templates_dir)
    assets_path = Path(assets_dir)

    # --- Sanity checks ---
    if not tpl_path.is_dir():
        raise SystemExit(f"Templates directory not found: {tpl_path}")
    _check_vendor(assets_path)

    # --- Jinja2 environment ---
    env = Environment(
        loader=FileSystemLoader(str(tpl_path)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["markdown"] = _markdown_to_html

    # --- Load data ---
    log.info("Loading content from %s …", data_path)
    trips = load_all_trips(data_path)
    log.info("Found %d trip(s).", len(trips))

    # --- Clean output directory ---
    if out_path.exists():
        shutil.rmtree(out_path)
    out_path.mkdir(parents=True)

    # --- Copy assets ---
    _copy_assets(assets_path, out_path)

    # --- Render trips index ---
    _render_trips_index(env, trips, out_path)

    # --- Render trip + entry pages ---
    for trip in trips:
        _render_trip_page(env, trip, out_path)
        for entry in trip["entries"]:
            _render_entry_page(env, trip, entry, out_path)

    log.info("Build complete → %s/", out_path)


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------


def _render_trips_index(
    env: Environment,
    trips: list[dict[str, Any]],
    out_path: Path,
) -> None:
    tpl = env.get_template("index.html")
    html = tpl.render(trips=trips, page_title="EchoTrail")
    _write(out_path / "index.html", html)
    log.info("Rendered trips index → index.html")


def _render_trip_page(
    env: Environment,
    trip: dict[str, Any],
    out_path: Path,
) -> None:
    tpl = env.get_template("trip.html")
    html = tpl.render(trip=trip, page_title=trip["title"])
    _write(out_path / "trips" / trip["id"] / "index.html", html)
    log.info("Rendered trip: %s", trip["id"])

    # Copy trip media (cover + entry media)
    _copy_trip_media(trip, out_path)


def _render_entry_page(
    env: Environment,
    trip: dict[str, Any],
    entry: dict[str, Any],
    out_path: Path,
) -> None:
    tpl = env.get_template("entry.html")
    page_title = entry["date"] or entry["id"]
    html = tpl.render(trip=trip, entry=entry, page_title=page_title)
    dest = out_path / "trips" / trip["id"] / "entries" / entry["id"] / "index.html"
    _write(dest, html)
    log.info("  Rendered entry: %s/%s", trip["id"], entry["id"])


def _copy_trip_media(trip: dict[str, Any], out_path: Path) -> None:
    """Copy trip cover image and all entry media files to dist/."""
    from pathlib import Path as _P

    # We need the original data path to copy from; reconstruct from URL
    # Convention: trip["url"] == "trips/<trip_id>/"
    # We rely on the caller's CWD being the project root.
    trip_src = _P("data") / "trips" / trip["id"]

    # Cover
    if trip["cover"]:
        src = trip_src / trip["cover"]
        dst = out_path / "trips" / trip["id"] / trip["cover"]
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Entry media
    for entry in trip["entries"]:
        entry_src = trip_src / "entries" / entry["id"] / "media"
        if not entry_src.is_dir():
            continue
        entry_dst = (
            out_path / "trips" / trip["id"] / "entries" / entry["id"] / "media"
        )
        if entry_dst.exists():
            shutil.rmtree(entry_dst)
        shutil.copytree(entry_src, entry_dst)
