# EchoTrail Helpers

This directory contains helper scripts for importing content into EchoTrail from various sources.

## FindPenguins Scraper

The `findpenguins_scraper.py` script scrapes a FindPenguins trip and converts it to EchoTrail format.

### Installation

Install the required dependencies:

```bash
pip install requests beautifulsoup4
```

Or install with the scraper optional dependencies:

```bash
pip install -e ".[scraper]"
```

### Usage

```bash
python helpers/findpenguins_scraper.py https://findpenguins.com/karoc/trip/winter-is-coming
```

This will create a folder structure at:

```
imported/trips/winter-is-coming/
├── description.md          # Trip metadata, source info, and description
├── import_summary.json     # Summary of the import process
└── entries/
  ├── 2025-11-10-entry-title/
  │   ├── text.md         # Entry content with TOML front matter and Markdown body
  │   ├── media.json      # Per-file media metadata (e.g. image descriptions)
    │   └── media/
  │       ├── original-photo-name.jpg
  │       └── another-photo-name.jpg
  └── 2025-11-13-another-entry/
        └── text.md
```

### Options

- `--output DIR`: Specify the base output directory (default: `imported`)
- `--verbose`, `-v`: Enable verbose logging for debugging

### Examples

```bash
# Basic usage
python helpers/findpenguins_scraper.py https://findpenguins.com/username/trip/my-trip

# Output to a different base directory
python helpers/findpenguins_scraper.py https://findpenguins.com/username/trip/my-trip --output data

# Verbose output for debugging
python helpers/findpenguins_scraper.py https://findpenguins.com/username/trip/my-trip -v
```

### What Gets Scraped

The scraper attempts to extract:

- **Trip level:**
  - Title
  - Description
  - Source metadata (`source`, `source_url`)

- **Entry level:**
  - Date
  - Title
  - Content converted to Markdown body
  - Location/country information
  - GPS coordinates (if available)
  - Weather and temperature (if available)
  - Images and photos
  - Image descriptions/captions (when available) written to `media.json`

### Integration with EchoTrail

The generated structure is already compatible with EchoTrail's expected `data/trips/...` layout.

You can build directly from the imported directory:

```bash
python -m echotrail_gen build --data imported --assets assets
```

If you want to merge the imported trip into an existing `data` directory, move or copy the trip folder under `data/trips/`:

```bash
# PowerShell
Move-Item imported/trips/winter-is-coming data/trips/

# bash
mv imported/trips/winter-is-coming data/trips/

# Build from your main data directory
python -m echotrail_gen build --data data --assets assets
```

### Limitations

- The scraper works best with publicly accessible FindPenguins trips
- Private trips may require authentication (not currently supported)
- Image quality depends on what's available in the source
- Some metadata may not be available depending on the trip's privacy settings

### Troubleshooting

If the scraper fails or produces incomplete results:

1. Check that the URL is correct and the trip is publicly accessible
2. Run with `--verbose` flag to see detailed logging
3. Check the `import_summary.json` file for information about what was scraped
4. The website structure may have changed - you may need to adjust the scraper

### Notes

- The scraper is respectful and includes appropriate delays between requests
- Images are downloaded to preserve the complete trip
- Entry files include a Markdown heading, which EchoTrail uses as the entry title
- The front matter preserves extracted metadata such as `country`, `weather`, `temperature_c`, and `point_name` when available
- EchoTrail reads `media.json` and renders image descriptions in the gallery (caption + lightbox text)
- The source URL is recorded in the trip description for reference
