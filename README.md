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
python -m pip install -e .
```

> Requires Python 3.12+. `markdown`, `pydantic` and `Pillow` are installed by default.

### 2. Build the site

```bash
python -m echotrail_gen build --data example_data --fetch-vendor
```

| Option            | Default           | Description                                       |
| ----------------- | ----------------- | ------------------------------------------------- |
| `--data DIR`      | `data`            | Root content directory                            |
| `--output DIR`    | `dist`            | Output directory                                  |
| `--templates DIR` | _(bundled theme)_ | Jinja2 templates                                  |
| `--assets DIR`    | _(bundled theme)_ | Static assets (CSS etc.)                          |
| `--fetch-vendor`  | off               | Download Leaflet into the output during the build |

When `--templates` and `--assets` are omitted the **bundled default theme** is
used automatically. This means a content-only repository does not need to carry
any theme files.

To fetch vendor libraries separately (for caching):

```bash
python -m echotrail_gen fetch-vendor            # downloads to assets/vendor/
python -m echotrail_gen build --data example_data --assets assets
```

When `--assets` is given, the bundled default assets are copied first and
then the custom directory is **overlaid** on top. This means pre-fetched
vendor files win while bundled files like `css/style.css` are preserved
automatically.

### 3. Deploy

Upload the contents of `dist/` to your webspace, or use the GitHub Action
described below.

### 4. Run the tests

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run automatically on every push to `main` via [GitHub Actions](.github/workflows/tests.yml).

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
            ├── description.md    # +++ front matter: title, odometer_km, …
            ├── route.geojson
            └── entries/
                └── 2025-07-01-oslo/
                    └── text.md   # +++ front matter: date, country, lat, lon, …
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
        uses: karoc123/EchoTrail@main # pin to a release tag once available
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

| Input            | Default             | Description                       |
| ---------------- | ------------------- | --------------------------------- |
| `data-dir`       | `data`              | Content directory                 |
| `output-dir`     | `dist`              | Output directory                  |
| `templates-dir`  | _(empty → bundled)_ | Custom Jinja2 templates           |
| `assets-dir`     | _(empty → bundled)_ | Custom assets (CSS etc.)          |
| `python-version` | `3.12`              | Python version                    |
| `fetch-vendor`   | `true`              | Download Leaflet during the build |

---

## Adding a trip

1. Create a directory under `data/trips/` using a unique slug as the name:

```
data/trips/2027-skandinavien/
```

2. Add a `description.md` file with TOML front matter (Hugo-style `+++` delimiters):

```markdown
+++
title = 'Skandinavien-Tour 2027'
odometer_km = '4.800'
vehicle = 'BMW R 1250 GS'
+++

# Skandinavien-Tour 2027

Three weeks through Norway, Sweden and Finland …
```

**Front matter keys (trip)**:

| Key           | Required | Description                       |
| ------------- | -------- | --------------------------------- |
| `title`       | Yes      | Trip title (displayed as heading) |
| `odometer_km` | No       | Total distance in km              |

Any additional key in the front matter is automatically picked up as extra metadata and shown on the trip page. For example, `vehicle = 'BMW R 1250 GS'` → labelled "Vehicle".

3. Optionally add the following files alongside `description.md`:

| File            | Description                                                   |
| --------------- | ------------------------------------------------------------- |
| `cover.jpg`     | Cover image (also `cover.jpeg` / `cover.png`)                 |
| `route.geojson` | Route as a GeoJSON FeatureCollection (preferred)              |
| `route.gpx`     | Route as a GPX file (auto-converted if no `.geojson` present) |
| `meta.json`     | Optional extra metadata (future-proof)                        |

---

## Adding an entry

Entries live inside `data/trips/<trip_id>/entries/` and represent individual waypoints (days, stops, sights, …).

1. Create a subdirectory — the name becomes the entry ID (using the date as a prefix is recommended):

```
data/trips/2027-skandinavien/entries/2027-06-15-oslo/
```

2. Add a `text.md` file with TOML front matter (Hugo-style `+++` delimiters):

```markdown
+++
date = 2027-06-15
country = 'Norway'
weather = 'Sunny, 18 °C feels like'
temperature_c = 20
lat = 59.9139
lon = 10.7522
point_name = 'Oslo – Harbour'
+++

# Arriving in Oslo

The ferry port welcomes me with bright sunshine …
```

**Front matter keys (entry)**:

| Key             | Required | Description                                |
| --------------- | -------- | ------------------------------------------ |
| `date`          | Yes      | Date, e.g. `2027-06-15` (TOML native date) |
| `country`       | No       | Country name                               |
| `weather`       | No       | Weather description                        |
| `temperature_c` | No       | Temperature in °C (integer)                |
| `lat`           | No       | Latitude of the location (WGS 84)          |
| `lon`           | No       | Longitude of the location (WGS 84)         |
| `point_name`    | No       | Display name for the map marker            |

Any additional key in the front matter is automatically picked up as extra metadata.

`lat`/`lon` replace the former `point.geojson` file — a GeoJSON Point Feature is generated internally.

3. Optionally add:

| File / Dir  | Description                                                                                                   |
| ----------- | ------------------------------------------------------------------------------------------------------------- |
| `media/`    | Directory — place photos (`.jpg`, `.png`, `.webp`, `.gif`, `.avif`) and videos (`.mp4`, `.webm`, `.mov`) here |
| `meta.json` | Optional extra metadata (future-proof)                                                                        |

---

## Project layout

```
EchoTrail/
├── echotrail_gen/                  # Generator package (Python)
│   ├── __init__.py
│   ├── __main__.py                 # python -m echotrail_gen
│   ├── cli.py                      # Argument parsing
│   ├── builder.py                  # Build pipeline
│   ├── schema.py                   # Data loading (Pydantic models)
│   ├── geo.py                      # GeoJSON / GPX helpers
│   ├── images.py                   # Image resizing / thumbnails
│   ├── vendor.py                   # Leaflet + GLightbox download helper
│   ├── default_templates/          # Bundled Jinja2 theme (English)
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── trip.html
│   │   └── entry.html
│   └── default_assets/             # Bundled static assets
│       ├── css/style.css
│       └── vendor/
│           ├── leaflet/            # Populated by fetch-vendor
│           └── glightbox/          # Populated by fetch-vendor
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
│   ├── test_images.py
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

### Architecture notes

- Content is loaded into typed `Trip` and `Entry` models (Pydantic) in `echotrail_gen/schema.py`, keeping parsing concerns separate from rendering.
- The build pipeline in `echotrail_gen/builder.py` consumes those models to render templates and copy media/assets.
- During the build, images are automatically resized to web-friendly dimensions (max 1600 px) and JPEG thumbnails (max 400 px) are generated for the gallery.
- The entry page shows a thumbnail grid with a [GLightbox](https://biati-digital.github.io/glightbox/) lightbox for full-screen browsing.
- All builds assume Python 3.12+; older Python versions are not supported.

---

## Data model reference

### Trip object (available in `trip.html` and `index.html`)

| Key                  | Type         | Description                                              |
| -------------------- | ------------ | -------------------------------------------------------- |
| `id`                 | str          | Directory name                                           |
| `title`              | str          | From front matter `title` in `description.md`            |
| `description_md`     | str          | Markdown body from `description.md` (after front matter) |
| `odometer_km`        | str          | From front matter `odometer_km` in `description.md`      |
| `cover`              | str or None  | Filename of cover image                                  |
| `route_geojson`      | dict or None | Parsed GeoJSON                                           |
| `route_geojson_json` | str          | JSON-serialised route (safe to embed in `<script>`)      |
| `entries`            | list         | List of Entry objects                                    |
| `extra`              | dict         | Extra front matter keys not in the known set             |
| `meta`               | dict         | Parsed `meta.json` (empty dict if absent)                |
| `url`                | str          | Relative URL from `dist/` root                           |

### Entry object (available in `entry.html` and within `trip.entries`)

| Key                  | Type         | Description                                                     |
| -------------------- | ------------ | --------------------------------------------------------------- |
| `id`                 | str          | Directory name                                                  |
| `trip_id`            | str          | Parent trip ID                                                  |
| `date`               | str          | From front matter `date` in `text.md`                           |
| `text_md`            | str          | Markdown body from `text.md` (after front matter)               |
| `country`            | str          | From front matter `country`                                     |
| `weather`            | str          | From front matter `weather`                                     |
| `temperature_c`      | str          | From front matter `temperature_c`                               |
| `point_geojson`      | dict or None | Parsed GeoJSON (generated from lat/lon)                         |
| `point_geojson_json` | str          | JSON-serialised point (safe to embed in `<script>`)             |
| `media`              | list         | List of `MediaItem(type=..., name=..., thumb_name=...)` objects |
| `extra`              | dict         | Extra front matter keys not in the known set                    |
| `meta`               | dict         | Parsed `meta.json` (empty dict if absent)                       |
| `url`                | str          | Relative URL from `dist/` root                                  |

---

## GPX support

If a trip directory contains `route.gpx` but **no** `route.geojson`, the GPX is automatically converted to GeoJSON during the build. Track points (`<trkpt>`) become a `LineString` feature; waypoints (`<wpt>`) become `Point` features.

To keep build times short, you can pre-convert your GPX files once and commit the resulting `.geojson` alongside them.

---

## Dependencies

| Package    | Required | Purpose                                 |
| ---------- | -------- | --------------------------------------- |
| `jinja2`   | Yes      | Template rendering                      |
| `markdown` | Yes      | Markdown rendering                      |
| `pydantic` | Yes      | Typed content models (Trip/Entry)       |
| `Pillow`   | Yes      | Image resizing and thumbnail generation |

No external geo libraries are needed — GeoJSON is parsed with the standard `json` module and GPX with `xml.etree.ElementTree`.
