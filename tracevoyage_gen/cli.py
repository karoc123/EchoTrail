"""CLI entry-point: ``python -m tracevoyage_gen [build|fetch-vendor]``."""

import argparse
import sys

from tracevoyage_gen.builder import build
from tracevoyage_gen.vendor import fetch_vendor


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tracevoyage_gen",
        description="TraceVoyage static site generator.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build", help="Build the static site into dist/.")
    build_parser.add_argument(
        "--data",
        default="data",
        metavar="DIR",
        help="Root data directory (default: data/).",
    )
    build_parser.add_argument(
        "--output",
        default="dist",
        metavar="DIR",
        help="Output directory (default: dist/).",
    )
    build_parser.add_argument(
        "--templates",
        default=None,
        metavar="DIR",
        help="Jinja2 templates directory (default: bundled theme).",
    )
    build_parser.add_argument(
        "--assets",
        default=None,
        metavar="DIR",
        help="Assets directory (default: bundled theme).",
    )
    build_parser.add_argument(
        "--fetch-vendor",
        action="store_true",
        default=False,
        help="Download Leaflet vendor files into the output during build.",
    )
    build_parser.add_argument(
        "--exclude-videos",
        action="store_true",
        default=False,
        help="Exclude video files from media galleries (reduces output size).",
    )

    fetch_parser = sub.add_parser(
        "fetch-vendor",
        help="Download vendored third-party JS/CSS (Leaflet) into assets/vendor/.",
    )
    fetch_parser.add_argument(
        "--assets",
        default="assets",
        metavar="DIR",
        help="Assets directory (default: assets/).",
    )

    args = parser.parse_args(argv)

    if args.command == "build":
        build(
            data_dir=args.data,
            output_dir=args.output,
            templates_dir=args.templates,
            assets_dir=args.assets,
            fetch_leaflet=args.fetch_vendor,
            skip_videos=args.exclude_videos,
        )
    elif args.command == "fetch-vendor":
        fetch_vendor(assets_dir=args.assets)


if __name__ == "__main__":
    main()
