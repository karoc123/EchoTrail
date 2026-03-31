# EchoTrail

A static travel-journal generator written in Python + Jinja2, with interactive maps powered by [Leaflet](https://leafletjs.com).

Content is kept **completely separate from the generator code**. The generated
site lands in `dist/` (never versioned) and can be deployed to any static
hosting — including GitHub Pages — via the built-in
[GitHub Action](#github-action).

---

## Quick start (local)

### 1. Install the generator

```bash
python -m pip install -e ".[markdown]"
```

> The optional `markdown` extra installs the `markdown` package for full
> Markdown rendering. Without it, a built-in minimal renderer handles the most
> common syntax.

### 2. Build the site

```bash
python -m echotrail_gen build --data example_data --fetch-vendor
```

| Option | Default | Description |
|---|---|---|
| `--data DIR` | `data` | Root content directory |
| `--output DIR` | `dist` | Output directory |
| `--templates DIR` | *(bundled theme)* | Jinja2 templates |
| `--assets DIR` | *(bundled theme)* | Static assets (CSS etc.) |
| `--fetch-vendor` | off | Download Leaflet into the output during the build |

When `--templates` and `--assets` are omitted the **bundled default theme** is
used automatically. This means a content-only repository does not need to carry
any theme files.

To fetch Leaflet separately (for caching):

```bash
python -m echotrail_gen fetch-vendor            # downloads to assets/vendor/leaflet/
python -m echotrail_gen build --data example_data --assets assets
```

### 3. Deploy

Upload the contents of `dist/` to your webspace, or use the GitHub Action
described below.

```bash
rsync -avz dist/ user@yourserver.de:/path/to/public_html/echotrail/
```

---

## GitHub Action

EchoTrail ships as a **composite GitHub Action**. This lets you keep a
minimal content repository and build + deploy automatically on every push.

### Minimal content repo layout

```
my-travel-journal/
├── .github/
│   └── workflows/
│       └── deploy.yml
└── data/
    └── trips/
        └── my-trip/
            ├── title.txt
            ├── description.md
            ├── route.geojson
            └── entries/
                └── 2025-07-01-oslo/
                    ├── date.txt
                    ├── text.md
                    └── point.geojson
```

### Example workflow (GitHub Pages)

```yaml
# .github/workflows/deploy.yml
name: Build & Deploy EchoTrail

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build with EchoTrail
        uses: karoc123/EchoTrail@main      # pin to a release tag once available
        with:
          data-dir: data
          # templates-dir and assets-dir default to the bundled theme

      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### Action inputs

| Input | Default | Description |
|---|---|---|
| `data-dir` | `data` | Content directory |
| `output-dir` | `dist` | Output directory |
| `templates-dir` | *(empty → bundled)* | Custom Jinja2 templates |
| `assets-dir` | *(empty → bundled)* | Custom assets (CSS etc.) |
| `python-version` | `3.12` | Python version |
| `fetch-vendor` | `true` | Download Leaflet during the build |

---

## Adding a trip

1. Create a directory under `data/trips/` using a unique slug as the name:

```
data/trips/2027-skandinavien/
```

2. Add the following files (all are optional except `title.txt`):

| File | Description |
|---|---|
| `title.txt` | Trip title (displayed as heading) |
| `description.md` | Long description in Markdown |
| `odometer_km.txt` | Total distance in km |
| `cover.jpg` | Cover image (also `cover.jpeg` / `cover.png`) |
| `route.geojson` | Route as a GeoJSON FeatureCollection (preferred) |
| `route.gpx` | Route as a GPX file (auto-converted if no `.geojson` present) |
| `meta.json` | Optional extra metadata (future-proof) |

Any additional `*.txt` file in the trip directory is automatically read as metadata and shown on the trip page. For example, `vehicle.txt` → labelled "Vehicle".

---

## Adding an entry

Entries live inside `data/trips/<trip_id>/entries/` and represent individual waypoints (days, stops, sights, …).

1. Create a subdirectory — the name becomes the entry ID (using the date as a prefix is recommended):

```
data/trips/2027-skandinavien/entries/2027-06-15-oslo/
```

2. Add the following files:

| File | Description |
|---|---|
| `date.txt` | Date string, e.g. `2027-06-15` |
| `text.md` | Journal text in Markdown |
| `point.geojson` | Location as a GeoJSON Point Feature |
| `country.txt` | Country name |
| `weather.txt` | Weather description |
| `temperature_c.txt` | Temperature in °C |
| `meta.json` | Optional extra metadata (future-proof) |
| `media/` | Directory — place photos (`.jpg`, `.png`, `.webp`, `.gif`, `.avif`) and videos (`.mp4`, `.webm`, `.mov`) here |

As with trips, any additional `*.txt` file is automatically picked up as metadata.

### Point GeoJSON format

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [13.4050, 52.5200]
  },
  "properties": {
    "name": "Berlin"
  }
}
```

Coordinates are `[longitude, latitude]` (GeoJSON standard).

---

## Project layout

```
EchoTrail/
├── echotrail_gen/                  # Generator package (Python)
│   ├── __init__.py
│   ├── __main__.py                 # python -m echotrail_gen
│   ├── cli.py                      # Argument parsing
│   ├── builder.py                  # Build pipeline
│   ├── schema.py                   # Data loading
│   ├── geo.py                      # GeoJSON / GPX helpers
│   ├── vendor.py                   # Leaflet download helper
│   ├── default_templates/          # Bundled Jinja2 theme
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── trip.html
│   │   └── entry.html
│   └── default_assets/             # Bundled static assets
│       ├── css/style.css
│       └── vendor/leaflet/         # Populated by fetch-vendor
│
├── example_data/                   # Example content (for testing/demo)
│   └── trips/
│       └── example-europe-trip/
│
├── tests/                          # Test suite
│   ├── conftest.py
│   ├── test_build.py
│   ├── test_cli.py
│   ├── test_geo.py
│   └── test_schema.py
│
├── action.yml                      # Composite GitHub Action
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Customising templates

Override the default theme by passing `--templates` and/or `--assets` pointing
to your own directories. The templates use
[Jinja2](https://jinja.palletsprojects.com/) and can be edited freely.

`base.html` defines the shared layout (header, footer, asset paths).
`index.html`, `trip.html`, and `entry.html` each `{% extends "base.html" %}`.

A `markdown()` helper is available in every template to render Markdown fields as HTML:

```html
{{ markdown(trip.description_md) }}
```

---

## Data model reference

### Trip object (available in `trip.html` and `index.html`)

| Key | Type | Description |
|---|---|---|
| `id` | str | Directory name |
| `title` | str | Content of `title.txt` |
| `description_md` | str | Raw Markdown from `description.md` |
| `odometer_km` | str | Content of `odometer_km.txt` |
| `cover` | str or None | Filename of cover image |
| `route_geojson` | dict or None | Parsed GeoJSON |
| `route_geojson_json` | str | JSON-serialised route (safe to embed in `<script>`) |
| `entries` | list | List of Entry objects |
| `extra` | dict | Extra `*.txt` metadata, keyed by stem |
| `meta` | dict | Parsed `meta.json` (empty dict if absent) |
| `url` | str | Relative URL from `dist/` root |

### Entry object (available in `entry.html` and within `trip.entries`)

| Key | Type | Description |
|---|---|---|
| `id` | str | Directory name |
| `trip_id` | str | Parent trip ID |
| `date` | str | Content of `date.txt` |
| `text_md` | str | Raw Markdown from `text.md` |
| `country` | str | Content of `country.txt` |
| `weather` | str | Content of `weather.txt` |
| `temperature_c` | str | Content of `temperature_c.txt` |
| `point_geojson` | dict or None | Parsed GeoJSON |
| `point_geojson_json` | str | JSON-serialised point (safe to embed in `<script>`) |
| `media` | list | List of `{"type": "image"/"video", "name": "…"}` dicts |
| `extra` | dict | Extra `*.txt` metadata, keyed by stem |
| `meta` | dict | Parsed `meta.json` (empty dict if absent) |
| `url` | str | Relative URL from `dist/` root |

---

## GPX support

If a trip directory contains `route.gpx` but **no** `route.geojson`, the GPX is automatically converted to GeoJSON during the build. Track points (`<trkpt>`) become a `LineString` feature; waypoints (`<wpt>`) become `Point` features.

To keep build times short, you can pre-convert your GPX files once and commit the resulting `.geojson` alongside them.

---

## Dependencies

| Package | Required | Purpose |
|---|---|---|
| `jinja2` | Yes | Template rendering |
| `markdown` | No (`[markdown]` extra) | Full Markdown rendering |
| `pytest` | No (`[test]` extra) | Running the test suite |

No external geo libraries are needed — GeoJSON is parsed with the standard `json` module and GPX with `xml.etree.ElementTree`. 