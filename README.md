# EchoTrail

EchoTrail is a static travel-journal generator built with Python and Jinja2.

Use this README for quick setup and daily usage.
For technical internals, see docs/ARCHITECTURE.md.

## Quick start

1. Install in editable mode:

```bash
python -m pip install -e .
```

2. Build a site:

```bash
python -m echotrail_gen build --data example_data --fetch-vendor
```

3. Open generated output:

- dist/index.html

## Build command reference

```bash
python -m echotrail_gen build [options]
```

| Option | Default | Description |
| --- | --- | --- |
| --data DIR | data | Root content directory |
| --output DIR | dist | Output directory |
| --templates DIR | bundled theme | Custom Jinja2 templates |
| --assets DIR | bundled theme | Custom assets |
| --fetch-vendor | off | Download Leaflet assets during build |
| --exclude-videos | off | Exclude videos from output as if they were not in input media |

Example for smaller output size:

```bash
python -m echotrail_gen build --data data --exclude-videos
```

## Vendor assets

If you do not use --fetch-vendor during build, fetch vendor files separately:

```bash
python -m echotrail_gen fetch-vendor
python -m echotrail_gen build --data data --assets assets
```

## Minimal content structure

```text
data/
  trips/
    my-trip/
      description.md
      route.geojson
      entries/
        2026-01-01-start/
          text.md
          media/
```

## Importing from FindPenguins

```bash
pip install -e ".[scraper]"
playwright install chromium
python helpers/findpenguins_scraper.py https://findpenguins.com/<user>/trip/<trip>
```

See helpers/README.md for details.

## GitHub Action

This repository includes a composite action in action.yml.

Inputs:

- data-dir
- output-dir
- templates-dir
- assets-dir
- python-version
- fetch-vendor
- exclude-videos

## Testing

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Documentation

- Quick usage: README.md
- Technical architecture: docs/ARCHITECTURE.md
