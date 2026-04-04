#!/usr/bin/env python3
"""Debug script to analyze FindPenguins page structure."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = 'https://findpenguins.com/karoc/trip/fahrradsommer-in-schweden'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

try:
    response = requests.get(url, timeout=30, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Überprüfe mapPreview Images
    print('=== mapPreview Images ===')
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if 'mapPreview' in src:
            print(f'Found mapPreview: {src[:150]}')
    
    # Überprüfe og:image
    print('\n=== og:image ===')
    og_image = soup.find('meta', attrs={'property': 'og:image'})
    if og_image:
        content = og_image.get('content', '')
        print(f'Found og:image: {content}')
    else:
        print('og:image not found')
    
    # Überprüfe alle img-Tags in Head
    print('\n=== All img in <head> ===')
    head = soup.find('head')
    if head:
        for img in head.find_all('img'):
            print(f'img: {img.get("src", "NO SRC")}')
    
    # Überprüfe alle Meta-Tags
    print('\n=== Meta tags with image/map ===')
    for meta in soup.find_all('meta'):
        prop = meta.get('property', '')
        name = meta.get('name', '')
        content = meta.get('content', '')
        if 'image' in prop.lower() or 'image' in name.lower() or 'map' in content.lower():
            print(f'{prop or name}: {content[:100]}')
    
    # Überprüfe div mit background-image
    print('\n=== Divs with background-image ===')
    for div in soup.find_all('div'):
        style = div.get('style', '')
        if 'background' in style.lower() and 'url' in style.lower():
            print(f'Found background-image: {style[:150]}')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
