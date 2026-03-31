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
imported/trip/winter-is-coming/
├── description.md          # Trip metadata and description
├── import_summary.json     # Summary of the import process
└── entries/
    ├── 2025-01-15-entry-title/
    │   ├── text.md         # Entry content with TOML front matter
    │   └── media/
    │       ├── image_001.jpg
    │       └── image_002.jpg
    └── 2025-01-16-another-entry/
        └── text.md
```

### Options

- `--output DIR`: Specify the base output directory (default: `imported`)
- `--verbose`, `-v`: Enable verbose logging for debugging

### Examples

```bash
# Basic usage
python helpers/findpenguins_scraper.py https://findpenguins.com/username/trip/my-trip

# Output to a different directory
python helpers/findpenguins_scraper.py https://findpenguins.com/username/trip/my-trip --output data

# Verbose output for debugging
python helpers/findpenguins_scraper.py https://findpenguins.com/username/trip/my-trip -v
```

### What Gets Scraped

The scraper attempts to extract:

- **Trip level:**
  - Title
  - Description
  - Cover image (if available)

- **Entry level:**
  - Date
  - Title
  - Content (text/markdown)
  - Location/country information
  - GPS coordinates (if available)
  - Images and photos

### Integration with EchoTrail

After scraping, you can move the imported content to your data directory:

```bash
# Move the scraped trip to your data directory
mv imported/trip/winter-is-coming data/trips/

# Build your site
python -m echotrail_gen build --data data --fetch-vendor
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
- All original metadata is preserved in the front matter
- The source URL is recorded in the trip description for reference
