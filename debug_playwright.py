#!/usr/bin/env python3
"""Debug script to check if Playwright includes og:image."""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = 'https://findpenguins.com/karoc/trip/fahrradsommer-in-schweden'

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Loading page with Playwright...")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Close cookie popup if present
        try:
            cookie_accept = page.locator('a[onclick*="acceptCookies"], button:has-text("Accept")')
            if cookie_accept.count() > 0:
                print("Closing cookie popup...")
                cookie_accept.first.click()
                page.wait_for_timeout(500)
        except:
            pass
        
        html = page.inner_html("body")
        browser.close()
        
        # Parse the HTML
        soup = BeautifulSoup("<html><body>" + html + "</body></html>", 'html.parser')
        
        # Überprüfe og:image
        print("\n=== Checking og:image in Playwright-rendered page ===")
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image:
            print(f'Found og:image: {og_image.get("content", "")}')
        else:
            print('og:image NOT found in Playwright-rendered page')
        
        # Überprüfe mit requests für Vergleich
        print("\n=== Checking og:image with requests for comparison ===")
        import requests
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=30, headers=headers)
        soup2 = BeautifulSoup(response.text, 'html.parser')
        og_image2 = soup2.find('meta', attrs={'property': 'og:image'})
        if og_image2:
            print(f'Found og:image: {og_image2.get("content", "")}')
        else:
            print('og:image NOT found with requests')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
