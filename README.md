# EchoTrail

A static travel-journal generator written in Python + Jinja2, with interactive maps powered by [Leaflet](https://leafletjs.com).

Content is kept **completely separate from the generator code** — German journal text lives in `data/`, English code lives everywhere else. The generated site lands in `dist/` (never versioned) and can be uploaded directly to any webspace.

---

## Quick start

### 1. Install the generator

```bash
python -m pip install -e ".[markdown]"
```

> The optional `markdown` extra installs the `markdown` package for full Markdown rendering.
> Without it, a built-in minimal renderer handles the most common syntax.

### 2. Vendor Leaflet (one-time setup)

```bash
python -m echotrail_gen fetch-vendor
```

This downloads Leaflet JS/CSS/images into `assets/vendor/leaflet/` so the site works **offline on your webspace** without any CDN dependency.

### 3. Build the site

```bash
python -m echotrail_gen build
```

| Option | Default | Description |
|---|---|---|
| `--data DIR` | `data/` | Root content directory |
| `--output DIR` | `dist/` | Output directory |
| `--templates DIR` | `templates/` | Jinja2 templates |
| `--assets DIR` | `assets/` | Static assets |

The generated site is written to `dist/`. Open `dist/index.html` in a browser to preview locally.

### 4. Upload to your webspace

Upload the entire contents of `dist/` to your webspace via FTP/SFTP/rsync, for example:

```bash
rsync -avz dist/ user@yourserver.de:/path/to/public_html/echotrail/
```

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
│           ├── title.txt
│           ├── description.md
│           ├── odometer_km.txt
│           ├── route.geojson
│           └── entries/
│               └── <entry_id>/
│                   ├── date.txt
│                   ├── text.md
│                   ├── point.geojson
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

No external geo libraries are needed — GeoJSON is parsed with the standard `json` module and GPX with `xml.etree.ElementTree`. 