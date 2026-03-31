# EchoTrail

A static travel-journal generator written in Python + Jinja2, with interactive maps powered by [Leaflet](https://leafletjs.com).

Content is kept **completely separate from the generator code** — German journal text lives in `data/`, English code lives everywhere else. The generated site lands in `dist/` (never versioned) and can be uploaded directly to any webspace.

---

## Quick start

### 1. Install the generator

```bash
python -m pip install -e .
```

> Requires Python 3.12+. The `markdown` renderer is installed by default.

### 2. Vendor Leaflet (one-time setup)

```bash
python -m echotrail_gen fetch-vendor
```

This downloads Leaflet JS/CSS/images into `assets/vendor/leaflet/` so the site works **offline on your webspace** without any CDN dependency.

### 3. Build the site

```bash
python -m echotrail_gen build
```

| Option            | Default      | Description            |
| ----------------- | ------------ | ---------------------- |
| `--data DIR`      | `data/`      | Root content directory |
| `--output DIR`    | `dist/`      | Output directory       |
| `--templates DIR` | `templates/` | Jinja2 templates       |
| `--assets DIR`    | `assets/`    | Static assets          |

The generated site is written to `dist/`. Open `dist/index.html` in a browser to preview locally.

### 4. Upload to your webspace

Upload the entire contents of `dist/` to your webspace via FTP/SFTP/rsync, for example:

```bash
rsync -avz dist/ user@yourserver.de:/path/to/public_html/echotrail/
```

### 5. Run the tests

```bash
python -m pip install -e ".[dev,markdown]"
python -m pytest tests/ -v
```

Tests run automatically on every push to `main` via [GitHub Actions](.github/workflows/tests.yml).

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

Drei Wochen durch Norwegen, Schweden und Finnland …
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
country = 'Norwegen'
weather = 'Sonnig, 18 °C gefühlt'
temperature_c = 20
lat = 59.9139
lon = 10.7522
point_name = 'Oslo – Hafen'
+++

# Ankunft in Oslo

Der Fährhafen empfängt mich mit strahlendem Sonnenschein …
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
├── echotrail_gen/          # Generator package (Python)
│   ├── __init__.py
│   ├── __main__.py         # python -m echotrail_gen
│   ├── cli.py              # Argument parsing
│   ├── builder.py          # Build pipeline
│   ├── schema.py           # Data loading
│   ├── geo.py              # GeoJSON / GPX helpers
│   └── vendor.py           # Leaflet download helper
│
├── data/                   # Your content (German text)
│   └── trips/
│       └── <trip_id>/
│           ├── description.md  # +++ front matter: title, odometer_km, …
│           ├── route.geojson
│           └── entries/
│               └── <entry_id>/
│                   ├── text.md  # +++ front matter: date, country, lat, lon, …
│                   └── media/
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html          # Trips overview
│   ├── trip.html           # Trip detail + route map
│   └── entry.html          # Entry detail + point map
│
├── assets/
│   ├── css/style.css
│   └── vendor/leaflet/     # Populated by fetch-vendor
│
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Customising templates

The templates in `templates/` use [Jinja2](https://jinja.palletsprojects.com/) and can be edited freely.

`base.html` defines the shared layout (header, footer, asset paths).
`index.html`, `trip.html`, and `entry.html` each `{% extends "base.html" %}`.

A `markdown()` helper is available in every template to render Markdown fields as HTML:

```html
{{ markdown(trip.description_md) }}
```

### Architecture notes

- Content is loaded into typed `Trip` and `Entry` models (Pydantic) in `echotrail_gen/schema.py`, keeping parsing concerns separate from rendering.
- The build pipeline in `echotrail_gen/builder.py` consumes those models to render templates and copy media/assets.
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

| Key                  | Type         | Description                                            |
| -------------------- | ------------ | ------------------------------------------------------ |
| `id`                 | str          | Directory name                                         |
| `trip_id`            | str          | Parent trip ID                                         |
| `date`               | str          | From front matter `date` in `text.md`                  |
| `text_md`            | str          | Markdown body from `text.md` (after front matter)      |
| `country`            | str          | From front matter `country`                            |
| `weather`            | str          | From front matter `weather`                            |
| `temperature_c`      | str          | From front matter `temperature_c`                      |
| `point_geojson`      | dict or None | Parsed GeoJSON                                         |
| `point_geojson_json` | str          | JSON-serialised point (safe to embed in `<script>`)    |
| `media`              | list         | List of `{"type": "image"/"video", "name": "…"}` dicts |
| `extra`              | dict         | Extra front matter keys not in the known set           |
| `meta`               | dict         | Parsed `meta.json` (empty dict if absent)              |
| `url`                | str          | Relative URL from `dist/` root                         |

---

## GPX support

If a trip directory contains `route.gpx` but **no** `route.geojson`, the GPX is automatically converted to GeoJSON during the build. Track points (`<trkpt>`) become a `LineString` feature; waypoints (`<wpt>`) become `Point` features.

To keep build times short, you can pre-convert your GPX files once and commit the resulting `.geojson` alongside them.

---

## Dependencies

| Package    | Required                | Purpose                                                     |
| ---------- | ----------------------- | ----------------------------------------------------------- |
| `jinja2`   | Yes                     | Template rendering                                          |
| `markdown` | Yes                     | Markdown rendering                                          |
| `pydantic` | Yes                     | Typed content models (Trip/Entry)                           |

No external geo libraries are needed — GeoJSON is parsed with the standard `json` module and GPX with `xml.etree.ElementTree`.
