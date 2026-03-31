#!/usr/bin/env python3
"""FindPenguins trip scraper for EchoTrail.

Scrapes a FindPenguins trip URL and creates an EchoTrail-compatible
folder structure with entries for each post from the trip.

Usage:
    python helpers/findpenguins_scraper.py https://findpenguins.com/karoc/trip/winter-is-coming

This will create:
    imported/trip/winter-is-coming/
        description.md
        entries/
            <entry-id>/
                text.md
                media/
                    <images>.jpg
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: This script requires 'requests' and 'beautifulsoup4'.", file=sys.stderr)
    print("Install with: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def sanitize_filename(text: str) -> str:
    """Convert text to a safe filesystem name."""
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def download_image(url: str, dest_path: Path, session: requests.Session) -> bool:
    """Download an image from URL to dest_path."""
    try:
        log.info(f"Downloading image: {url}")
        response = session.get(url, timeout=30, stream=True)
        response.raise_for_status()

        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        log.warning(f"Failed to download {url}: {e}")
        return False


def extract_coordinates(soup: BeautifulSoup) -> tuple[float | None, float | None]:
    """Try to extract GPS coordinates from the page."""
    # Try to find coordinates in meta tags
    for meta in soup.find_all('meta'):
        prop = meta.get('property', '')
        if 'latitude' in prop.lower():
            try:
                return float(meta.get('content', '')), None
            except ValueError:
                pass
        if 'longitude' in prop.lower():
            try:
                return None, float(meta.get('content', ''))
            except ValueError:
                pass

    # Try to find coordinates in scripts (common pattern)
    for script in soup.find_all('script'):
        script_text = script.string
        if script_text:
            # Look for patterns like lat: 52.52, lng: 13.405
            lat_match = re.search(r'lat(?:itude)?["\s:]+(-?\d+\.?\d*)', script_text, re.I)
            lon_match = re.search(r'lon(?:g|gitude)?["\s:]+(-?\d+\.?\d*)', script_text, re.I)
            if lat_match and lon_match:
                try:
                    return float(lat_match.group(1)), float(lon_match.group(1))
                except ValueError:
                    pass

    return None, None


def scrape_findpenguins_trip(url: str, output_base: Path = Path("imported")) -> None:
    """Scrape a FindPenguins trip and create EchoTrail folder structure.

    Args:
        url: FindPenguins trip URL (e.g., https://findpenguins.com/karoc/trip/winter-is-coming)
        output_base: Base directory for output (default: 'imported')
    """
    # Parse URL to extract trip information
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]

    if len(path_parts) < 3 or path_parts[-2] != 'trip':
        log.error(f"Invalid FindPenguins trip URL format. Expected: .../trip/trip-name")
        return

    username = path_parts[0]
    trip_slug = path_parts[-1]

    # Create output directory structure
    trip_dir = output_base / "trip" / trip_slug
    entries_dir = trip_dir / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Scraping trip: {url}")
    log.info(f"Output directory: {trip_dir}")

    # Create a session for reusing connections
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        # Fetch the main trip page
        log.info("Fetching trip page...")
        response = session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract trip title
        trip_title = soup.find('h1')
        if trip_title:
            trip_title = trip_title.get_text(strip=True)
        else:
            trip_title = trip_slug.replace('-', ' ').title()

        # Extract trip description
        trip_description = ""
        description_elem = soup.find('div', class_=re.compile(r'description|about|intro', re.I))
        if description_elem:
            trip_description = description_elem.get_text(strip=True)

        # Create trip description.md
        description_content = f"""+++
title = '{trip_title}'
source = 'FindPenguins'
source_url = '{url}'
+++

# {trip_title}

{trip_description or 'Imported from FindPenguins.'}
"""

        (trip_dir / "description.md").write_text(description_content, encoding='utf-8')
        log.info(f"Created trip description: {trip_dir / 'description.md'}")

        # Find all entries/posts
        # FindPenguins typically structures posts with specific classes
        # This is a generalized approach that should work for most travel blogs
        entries = []

        # Try multiple possible selectors for posts/entries
        post_selectors = [
            'article',
            '.post', '.entry', '.footprint',
            '[class*="post"]', '[class*="entry"]', '[class*="footprint"]'
        ]

        posts = []
        for selector in post_selectors:
            posts = soup.select(selector)
            if posts:
                log.info(f"Found {len(posts)} posts using selector: {selector}")
                break

        if not posts:
            log.warning("No posts found with standard selectors. Trying alternative approach...")
            # Try to find links to individual posts
            post_links = soup.find_all('a', href=re.compile(r'/footprint/\d+'))
            if post_links:
                log.info(f"Found {len(post_links)} post links")
                # Fetch each individual post
                for i, link in enumerate(post_links, 1):
                    post_url = urljoin(url, link.get('href'))
                    try:
                        log.info(f"Fetching post {i}/{len(post_links)}: {post_url}")
                        post_response = session.get(post_url, timeout=30)
                        post_response.raise_for_status()
                        post_soup = BeautifulSoup(post_response.text, 'html.parser')
                        posts.append(post_soup)
                    except Exception as e:
                        log.warning(f"Failed to fetch post {post_url}: {e}")

        if not posts:
            log.error("Could not find any posts. The page structure may have changed.")
            log.info("Creating a minimal trip structure with the main page content.")

            # Create a single entry with the main content
            entry_id = f"{datetime.now().strftime('%Y-%m-%d')}-{trip_slug}"
            entry_dir = entries_dir / entry_id
            entry_dir.mkdir(parents=True, exist_ok=True)

            main_content = soup.find('main') or soup.find('body')
            content_text = main_content.get_text(strip=True) if main_content else "No content found."

            entry_content = f"""+++
date = {datetime.now().date()}
country = ''
weather = ''
+++

# Trip Content

{content_text[:1000]}...
"""
            (entry_dir / "text.md").write_text(entry_content, encoding='utf-8')
            log.info(f"Created minimal entry: {entry_dir}")
            return

        # Process each post
        log.info(f"Processing {len(posts)} posts...")
        for idx, post in enumerate(posts, 1):
            try:
                # Extract post title
                title_elem = post.find(['h1', 'h2', 'h3'])
                title = title_elem.get_text(strip=True) if title_elem else f"Entry {idx}"

                # Extract date
                date_elem = post.find('time')
                date_str = None
                if date_elem:
                    date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)

                # Try to parse date
                entry_date = None
                if date_str:
                    for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d.%m.%Y', '%m/%d/%Y']:
                        try:
                            entry_date = datetime.strptime(date_str[:10], fmt).date()
                            break
                        except ValueError:
                            continue

                if not entry_date:
                    entry_date = datetime.now().date()

                # Create entry ID
                entry_id = f"{entry_date}-{sanitize_filename(title)}"
                entry_dir = entries_dir / entry_id
                entry_dir.mkdir(parents=True, exist_ok=True)

                log.info(f"Processing entry {idx}/{len(posts)}: {entry_id}")

                # Extract location/country
                location = ""
                country = ""
                location_elem = post.find(class_=re.compile(r'location|place|country', re.I))
                if location_elem:
                    location = location_elem.get_text(strip=True)
                    # Try to extract country from location
                    parts = location.split(',')
                    if parts:
                        country = parts[-1].strip()

                # Extract coordinates
                lat, lon = extract_coordinates(post)

                # Extract content
                content_elem = post.find(class_=re.compile(r'content|body|text', re.I))
                if not content_elem:
                    # Get all paragraphs
                    content_elem = post

                content_text = ""
                for p in content_elem.find_all(['p', 'div']):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # Skip very short divs
                        content_text += f"\n\n{text}"

                # Extract images
                media_dir = entry_dir / "media"
                images = post.find_all('img')
                image_count = 0

                if images:
                    media_dir.mkdir(exist_ok=True)

                    for img_idx, img in enumerate(images, 1):
                        img_url = img.get('src') or img.get('data-src')
                        if not img_url:
                            continue

                        # Skip small images (icons, avatars, etc.)
                        width = img.get('width', '')
                        height = img.get('height', '')
                        try:
                            if width and int(width) < 100:
                                continue
                            if height and int(height) < 100:
                                continue
                        except ValueError:
                            pass

                        # Make URL absolute
                        img_url = urljoin(url, img_url)

                        # Determine file extension
                        ext = '.jpg'
                        if '.png' in img_url.lower():
                            ext = '.png'
                        elif '.webp' in img_url.lower():
                            ext = '.webp'

                        img_filename = f"image_{img_idx:03d}{ext}"
                        img_path = media_dir / img_filename

                        if download_image(img_url, img_path, session):
                            image_count += 1

                # Create entry text.md with TOML front matter
                entry_content = "+++\n"
                entry_content += f"date = {entry_date}\n"
                if country:
                    entry_content += f"country = '{country}'\n"
                if location:
                    entry_content += f"point_name = '{location}'\n"
                if lat is not None and lon is not None:
                    entry_content += f"lat = {lat}\n"
                    entry_content += f"lon = {lon}\n"
                entry_content += "+++\n\n"
                entry_content += f"# {title}\n"
                entry_content += content_text.strip()

                (entry_dir / "text.md").write_text(entry_content, encoding='utf-8')

                log.info(f"  Created entry: {entry_dir}")
                if image_count > 0:
                    log.info(f"  Downloaded {image_count} images")

                entries.append({
                    'id': entry_id,
                    'title': title,
                    'date': str(entry_date),
                    'images': image_count
                })

            except Exception as e:
                log.error(f"Failed to process post {idx}: {e}", exc_info=True)
                continue

        # Create a summary
        summary = {
            'trip_title': trip_title,
            'trip_slug': trip_slug,
            'source_url': url,
            'scraped_at': datetime.now().isoformat(),
            'entries_count': len(entries),
            'entries': entries
        }

        summary_path = trip_dir / "import_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

        log.info(f"\n{'='*60}")
        log.info(f"Scraping completed successfully!")
        log.info(f"Trip: {trip_title}")
        log.info(f"Entries created: {len(entries)}")
        log.info(f"Output directory: {trip_dir}")
        log.info(f"Summary: {summary_path}")
        log.info(f"{'='*60}\n")

    except requests.RequestException as e:
        log.error(f"Failed to fetch trip page: {e}")
        sys.exit(1)
    except Exception as e:
        log.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape a FindPenguins trip and convert to EchoTrail format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python helpers/findpenguins_scraper.py https://findpenguins.com/karoc/trip/winter-is-coming
  python helpers/findpenguins_scraper.py https://findpenguins.com/user/trip/my-trip --output data
        """
    )
    parser.add_argument(
        'url',
        help='FindPenguins trip URL (e.g., https://findpenguins.com/karoc/trip/winter-is-coming)'
    )
    parser.add_argument(
        '--output',
        default='imported',
        help='Base output directory (default: imported)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_path = Path(args.output)
    scrape_findpenguins_trip(args.url, output_path)


if __name__ == '__main__':
    main()
