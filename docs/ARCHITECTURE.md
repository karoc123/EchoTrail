# EchoTrail Architecture

This document describes the technical internals of EchoTrail.

## High-level flow

1. CLI parses command arguments in echotrail_gen/cli.py.
2. Builder orchestrates the pipeline in echotrail_gen/builder.py.
3. Schema loader reads content from disk into typed Pydantic models in echotrail_gen/schema.py.
4. Templates render HTML via Jinja2.
5. Assets and media are copied/processed into the output directory.

## Build pipeline

Main entry point:

- python -m echotrail_gen build

Main orchestration function:

- build(...) in echotrail_gen/builder.py

Pipeline steps:

1. Validate template/assets setup.
2. Create Jinja2 environment.
3. Load trips from data/trips via load_all_trips(...).
4. Sort trips by start_date descending (newest first).
5. Render:
   - index page
   - trip pages
   - entry pages
6. Copy/process media:
   - images resized for web
   - thumbnails generated
   - optional video exclusion with skip_videos/exclude-videos

## CLI and options

Local CLI options are defined in echotrail_gen/cli.py.

Important build flags:

- --data DIR
- --output DIR
- --templates DIR
- --assets DIR
- --fetch-vendor
- --exclude-videos

When --exclude-videos is enabled, videos are treated as if they are not present in input media directories:

- they are removed from Entry.media
- they are not referenced in generated HTML
- they are not copied into dist

## Data loading model

Data is loaded into immutable Pydantic objects.

### Trip

Key fields:

- id
- title
- description_md
- odometer_km
- cover
- route_geojson / route_geojson_json
- entries
- visited_countries
- start_date
- duration_days
- extra
- meta
- source_dir

Derived fields:

- start_date: earliest entry date
- duration_days: inclusive days between first and last entry

### Entry

Key fields:

- id
- trip_id
- date
- title
- text_md
- country
- country_flag
- point_geojson / point_geojson_json
- media
- extra
- meta

### MediaItem

Key fields:

- type (image/video)
- name
- thumb_name
- description

## Templates

Bundled templates are in echotrail_gen/default_templates:

- base.html
- index.html
- trip.html
- entry.html

Templates extend base.html and use a markdown() helper from the builder.

## Media processing

Implementation lives in echotrail_gen/images.py.

For image files:

- web image: max 1600px, JPEG
- thumbnail: max 400px, JPEG

Video files:

- copied unchanged by default
- skipped entirely when skip_videos=True

## Mapping and geography

- Country to flag mapping in echotrail_gen/schema.py.
- Route loading supports GeoJSON directly and GPX fallback conversion.

## GitHub Action

Composite action definition: action.yml.

Inputs include:

- data-dir
- output-dir
- templates-dir
- assets-dir
- python-version
- fetch-vendor
- exclude-videos

The action forwards those to the local CLI build command.
