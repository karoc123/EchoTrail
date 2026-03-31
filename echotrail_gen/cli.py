"""CLI entry-point: ``python -m echotrail_gen [build|fetch-vendor]``."""

import argparse
import sys

from echotrail_gen.builder import build
from echotrail_gen.vendor import fetch_vendor


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="echotrail_gen",
        description="EchoTrail static site generator.",
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
        default="templates",
        metavar="DIR",
        help="Jinja2 templates directory (default: templates/).",
    )
    build_parser.add_argument(
        "--assets",
        default="assets",
        metavar="DIR",
        help="Assets directory (default: assets/).",
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
        )
    elif args.command == "fetch-vendor":
        fetch_vendor(assets_dir=args.assets)


if __name__ == "__main__":
    main()
