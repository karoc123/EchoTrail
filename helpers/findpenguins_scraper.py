#!/usr/bin/env python3
"""FindPenguins trip scraper for EchoTrail.

Scrapes a FindPenguins trip URL and creates an EchoTrail-compatible
folder structure with entries for each post from the trip.

Usage:
    python helpers/findpenguins_scraper.py https://findpenguins.com/karoc/trip/winter-is-coming

This will create:
    imported/trips/winter-is-coming/
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
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("ERROR: This script requires 'requests' and 'beautifulsoup4'.", file=sys.stderr)
    print("Install with: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Image URL suffix patterns on FindPenguins CDN
# _t_s = tiny square, _m_s = medium small, _l = large
_IMG_SIZE_RE = re.compile(r'_(?:t_s|m_s|l)\.')


def sanitize_filename(text: str) -> str:
    """Convert text to a safe filesystem name."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def download_image(url: str, dest_path: Path, session: requests.Session) -> bool:
    """Download an image from URL to dest_path."""
    try:
        log.debug(f"Downloading image: {url}")
        response = session.get(url, timeout=30, stream=True)
        response.raise_for_status()

        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        log.warning(f"Failed to download {url}: {e}")
        return False


def _img_url_to_large(url: str) -> str:
    """Convert any FindPenguins image URL to the _l (large) variant."""
    return _IMG_SIZE_RE.sub('_l.', url)


def _parse_desc_span(desc_span: Tag) -> dict[str, Any]:
    """Parse the .desc span that contains date, country, and weather.

    Typical text: "Nov 10–11, 2025 in Germany ⋅ ⛅ 6 °C"
    The element also has a `content` attribute with ISO date like "2025-11-10".
    """
    info: dict[str, Any] = {}

    # Date from the content attribute (ISO format)
    iso_date = desc_span.get('content', '')
    if iso_date:
        try:
            info['date'] = datetime.strptime(iso_date[:10], '%Y-%m-%d').date()
        except ValueError:
            pass

    text = desc_span.get_text(' ', strip=True)

    # Country: "... in <Country> ⋅ ..."
    country_match = re.search(r'\bin\s+([A-Za-zÀ-ÿ\s-]+?)(?:\s*⋅|$)', text)
    if country_match:
        info['country'] = country_match.group(1).strip()

    # Weather emoji + temperature: "⋅ ⛅ 6 °C" or "⋅ ☁️ 9 °C"
    weather_match = re.search(r'⋅\s*(.+)', text)
    if weather_match:
        weather_raw = weather_match.group(1).strip()
        info['weather'] = weather_raw

        temp_match = re.search(r'(-?\d+)\s*°C', weather_raw)
        if temp_match:
            info['temperature_c'] = temp_match.group(1)

    return info


def _extract_entry_text(article: Tag) -> str:
    """Extract the body text from an article, combining truncated and hidden parts."""
    text_div = article.find('div', class_='text')
    if not text_div:
        return ""

    # Remove "Read more" links
    for a in text_div.find_all('a', class_='readMore'):
        a.decompose()

    # The truncated text ends right before <span class="dots"> and the
    # continuation lives in <span class="rest hide">.  Unwrap the rest
    # span so its text stays inline in the <p>.
    for rest_span in text_div.find_all('span', class_='rest'):
        rest_span.unwrap()

    for dots in text_div.find_all('span', class_='dots'):
        dots.decompose()

    paragraphs = []
    for p in text_div.find_all('p'):
        # Use separator to preserve word boundaries, then normalise whitespace
        t = p.get_text(' ')
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            paragraphs.append(t)

    return '\n\n'.join(paragraphs)


def _extract_photos(article: Tag, base_url: str) -> list[dict[str, str]]:
    """Extract photo URLs from the .images-container in an article.

    Returns list of dicts with 'url' (large version), 'filename', and
    optional 'description'.
    """
    photos: list[dict[str, str]] = []
    container = article.find('div', class_='images-container')
    if not container:
        return photos

    for a_tag in container.find_all('a', class_='image'):
        data_url = a_tag.get('data-url', '')
        data_filename = a_tag.get('data-filename', '')
        if not data_url:
            continue

        # Make absolute and ensure large variant
        abs_url = urljoin(base_url, data_url)
        abs_url = _img_url_to_large(abs_url)

        filename = data_filename or abs_url.split('/')[-1]

        # Try multiple possible caption sources used in FindPenguins markup.
        desc_candidates = [
            a_tag.get('data-description', ''),
            a_tag.get('data-caption', ''),
            a_tag.get('title', ''),
            a_tag.get('aria-label', ''),
        ]

        img_tag = a_tag.find('img')
        if img_tag:
            desc_candidates.extend([
                img_tag.get('alt', ''),
                img_tag.get('title', ''),
            ])

        caption = ""
        for candidate in desc_candidates:
            cleaned = re.sub(r'\s+', ' ', candidate).strip()
            if cleaned:
                caption = cleaned
                break

        photos.append({'url': abs_url, 'filename': filename, 'description': caption})

    return photos


def _fetch_page_with_playwright(url: str) -> str | None:
    """Fetch a trip page using Playwright to handle dynamic 'Load more' buttons.

    Returns the full page HTML after all dynamically loaded articles are fetched,
    or None if Playwright is not available.
    """
    if not HAS_PLAYWRIGHT:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Close cookie popup if present (FindPenguins uses one)
            try:
                cookie_accept = page.locator('a[onclick*="acceptCookies"], button:has-text("Accept")')
                if cookie_accept.count() > 0:
                    log.debug("  Accepting cookies popup")
                    cookie_accept.first.click()
                    page.wait_for_timeout(500)
            except Exception as e:
                log.debug(f"  No cookie popup found: {e}")

            # Poll for "Load more" button and click it until articles stop loading
            max_iterations = 100  # Safety limit
            iteration = 0
            while iteration < max_iterations:
                try:
                    # Look for the "Load more" button (German: "Mehr" or English text)
                    load_more = page.locator(
                        'button:has-text("Load more"), button:has-text("Mehr"), a:has-text("Load more"), a.loadmoreBtn'
                    )

                    if load_more.count() > 0:
                        log.debug(f"  Clicking 'Load more' button (iteration {iteration + 1})")
                        # Scroll into view and click
                        load_more.first.scroll_into_view_if_needed()
                        load_more.first.click()
                        # Wait for new articles to render
                        page.wait_for_timeout(2000)
                        iteration += 1
                    else:
                        log.debug("  No more 'Load more' button found")
                        break
                except Exception as e:
                    log.debug(f"  No more buttons to click or error: {e}")
                    break

            html = page.inner_html("body")
            browser.close()
            return html

    except Exception as e:
        log.warning(f"Playwright loading failed, falling back to requests: {e}")
        return None


def _fetch_coordinates(
    footprint_url: str, session: requests.Session
) -> tuple[float | None, float | None]:
    """Fetch an individual footprint page and extract coordinates.

    Coordinates live in a script like:
        MapSingleFootprintController.initMap(51.815978,12.338218)
    """
    try:
        log.debug(f"Fetching coordinates from: {footprint_url}")
        resp = session.get(footprint_url, timeout=30)
        resp.raise_for_status()

        match = re.search(
            r'initMap\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)', resp.text
        )
        if match:
            return float(match.group(1)), float(match.group(2))
    except Exception as e:
        log.warning(f"Failed to fetch coordinates from {footprint_url}: {e}")

    return None, None


def scrape_findpenguins_trip(
    url: str,
    output_base: Path = Path("imported"),
    use_browser: bool = True,
) -> None:
    """Scrape a FindPenguins trip and create EchoTrail folder structure.

    Args:
        url: FindPenguins trip URL
        output_base: Base directory for output (default: 'imported')
        use_browser: Use Playwright browser for dynamic loading (default: True)
    """
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]

    if len(path_parts) < 3 or path_parts[-2] != 'trip':
        log.error("Invalid FindPenguins trip URL format. Expected: .../trip/trip-name")
        return

    trip_slug = path_parts[-1]

    trip_dir = output_base / "trips" / trip_slug
    entries_dir = trip_dir / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Scraping trip: {url}")
    log.info(f"Output directory: {trip_dir}")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        # Try Playwright first for dynamic loading, fall back to requests if unavailable
        html_content = None
        if use_browser:
            log.info("Fetching trip page with browser (for dynamic loading)...")
            html_content = _fetch_page_with_playwright(url)

        if html_content is None:
            log.info("Fetching trip page with requests...")
            response = session.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')

        # --- Trip metadata ---
        trip_title = None
        h1 = soup.find('h1')
        if h1:
            trip_title = h1.get_text(strip=True)
        if not trip_title:
            trip_title = trip_slug.replace('-', ' ').title()

        trip_description = ""
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            trip_description = og_desc.get('content', '')

        description_content = f"""\
+++
title = '{trip_title}'
source = 'FindPenguins'
source_url = '{url}'
+++

# {trip_title}

{trip_description or 'Imported from FindPenguins.'}
"""
        (trip_dir / "description.md").write_text(description_content, encoding='utf-8')
        log.info(f"Created trip description: {trip_dir / 'description.md'}")

        # --- Find articles ---
        articles = soup.find_all('article')
        if not articles:
            log.error("Could not find any <article> elements. The page structure may have changed.")
            return

        log.info(f"Found {len(articles)} entries. Processing...")

        entries: list[dict[str, Any]] = []

        for idx, article in enumerate(articles, 1):
            try:
                # --- Title ---
                title_elem = article.find('h2', class_='headline')
                title = title_elem.get_text(strip=True) if title_elem else f"Entry {idx}"

                # --- Footprint URL (for coordinates) ---
                footprint_link = None
                if title_elem:
                    a_tag = title_elem.find('a', href=True)
                    if a_tag:
                        footprint_link = a_tag['href']
                        if not footprint_link.startswith('http'):
                            footprint_link = urljoin(url, footprint_link)

                # --- Date, country, weather from .desc span ---
                desc_span = article.find('span', class_='desc')
                meta = _parse_desc_span(desc_span) if desc_span else {}

                entry_date = meta.get('date', datetime.now().date())
                country = meta.get('country', '')
                weather = meta.get('weather', '')
                temperature_c = meta.get('temperature_c', '')

                # --- Entry ID and directory ---
                entry_id = f"{entry_date}-{sanitize_filename(title)}"
                entry_dir = entries_dir / entry_id
                entry_dir.mkdir(parents=True, exist_ok=True)

                log.info(f"[{idx}/{len(articles)}] {entry_id}")

                # --- Coordinates (requires fetching individual page) ---
                lat, lon = None, None
                if footprint_link:
                    lat, lon = _fetch_coordinates(footprint_link, session)
                    if lat is not None:
                        log.debug(f"  Coordinates: {lat}, {lon}")
                    time.sleep(0.3)  # polite delay

                # --- Text content ---
                content_text = _extract_entry_text(article)

                # --- Photos ---
                photos = _extract_photos(article, url)
                image_count = 0
                media_items: list[dict[str, str]] = []
                if photos:
                    media_dir = entry_dir / "media"
                    media_dir.mkdir(exist_ok=True)
                    for photo in photos:
                        dest = media_dir / photo['filename']
                        if download_image(photo['url'], dest, session):
                            image_count += 1
                            media_items.append({
                                'name': photo['filename'],
                                'description': photo.get('description', ''),
                            })

                if media_items:
                    media_json_path = entry_dir / "media.json"
                    media_json_path.write_text(
                        json.dumps({'media': media_items}, indent=2, ensure_ascii=False),
                        encoding='utf-8',
                    )

                # --- Write text.md ---
                lines = ["+++"]
                lines.append(f"date = {entry_date}")
                if country:
                    lines.append(f"country = '{country}'")
                if weather:
                    lines.append(f"weather = '{weather}'")
                if temperature_c:
                    lines.append(f"temperature_c = {temperature_c}")
                if lat is not None and lon is not None:
                    lines.append(f"lat = {lat}")
                    lines.append(f"lon = {lon}")
                    lines.append(f"point_name = '{title}'")
                lines.append("+++")
                lines.append("")
                lines.append(f"# {title}")
                lines.append("")
                lines.append(content_text.strip())

                (entry_dir / "text.md").write_text(
                    '\n'.join(lines) + '\n', encoding='utf-8'
                )

                log.info(f"  {image_count} photos, country={country or '?'}, coords={'yes' if lat else 'no'}")

                entries.append({
                    'id': entry_id,
                    'title': title,
                    'date': str(entry_date),
                    'country': country,
                    'lat': lat,
                    'lon': lon,
                    'images': image_count,
                })

            except Exception as e:
                log.error(f"Failed to process entry {idx}: {e}", exc_info=True)
                continue

        # --- Summary ---
        summary = {
            'trip_title': trip_title,
            'trip_slug': trip_slug,
            'source_url': url,
            'scraped_at': datetime.now().isoformat(),
            'entries_count': len(entries),
            'entries': entries,
        }

        summary_path = trip_dir / "import_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

        log.info(f"\n{'='*60}")
        log.info(f"Scraping completed!")
        log.info(f"Trip: {trip_title}")
        log.info(f"Entries: {len(entries)}")
        log.info(f"Output: {trip_dir}")
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
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Skip Playwright browser and use requests only (misses dynamically loaded content)'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_path = Path(args.output)
    use_browser = not args.no_browser
    if not HAS_PLAYWRIGHT and use_browser:
        log.warning(
            "Playwright not installed. Install it with: pip install playwright\n"
            "Then run: playwright install chromium\n"
            "Falling back to requests (may miss dynamically loaded articles).")

    scrape_findpenguins_trip(args.url, output_path, use_browser=use_browser)


if __name__ == '__main__':
    main()
