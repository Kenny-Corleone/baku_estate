"""
EvTap — Bina.az parser
HTML və __NEXT_DATA__-dan elanları çıxarır
"""
import requests, random, re, time, json
from bs4 import BeautifulSoup
from .base import (make_id, clean_price, clean_text, detect_property_type, 
                   detect_deal_type, make_listing, extract_rooms, extract_area, extract_floor, fetch_rendered)

SOURCE = 'bina'
SOURCE_NAME = 'Bina.az'
BASE_URL = 'https://bina.az'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

# Kirayə və satış üçün ayrı URL-lər
URLS = {
    'kiraye': 'https://bina.az/baki/kiraye/menziller?page={page}',
    'satis': 'https://bina.az/baki/alqi-satqi/menziller?page={page}',
}


def parse_bina(pages=2):
    results = []
    for deal_type, url_template in URLS.items():
        for page in range(1, pages + 1):
            url = url_template.format(page=page)
            print(f"  Yüklənir: {url}")
            items = _fetch_listings(url, deal_type)
            print(f"  Bina [{deal_type}] səhifə {page}: {len(items)} elan")
            results.extend(items)
            time.sleep(random.uniform(1.5, 2.5))
    print(f"  Bina cəmi: {len(results)}")
    return results


def _fetch_listings(url, deal_type='kiraye'):
    """Fetch listings from rendered HTML page (Playwright)"""
    try:
        soup = fetch_rendered(url, timeout=45, wait_until='domcontentloaded', wait_for_selector='.item-card')
        if not soup:
            return []

        cards = soup.select('.item-card')
        if not cards:
            cards = (soup.select('[class*="items-i"]') or
                     soup.select('[class*="item-"]') or
                     soup.select('article') or
                     soup.select('[data-item-id]'))

        items = []
        for card in cards:
            try:
                item = _parse_html_card(card, deal_type)
                if item:
                    items.append(item)
            except Exception:
                pass

        return items
    except Exception as e:
        print(f"  ❌ Bina xəta: {e}")
        return []


def _parse_html_card(card, deal_type='kiraye'):
    """Parse a single listing card from HTML"""
    # Get link
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = href if href.startswith('http') else BASE_URL + href
    
    # Extract ID
    m = re.search(r'/items/(\d+)', href)
    if not m:
        m = re.search(r'[-_](\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)
    
    full_text = card.get_text(' ', strip=True)
    
    # Price
    price_el = (card.select_one('[class*="price"]') or
                card.select_one('.price-val') or
                card.select_one('.price'))
    price = clean_price(price_el.get_text()) if price_el else None

    # Title
    title_el = (card.select_one('[class*="title"]') or
                card.select_one('.card-title') or
                card.select_one('h2') or card.select_one('h3'))
    title = clean_text(title_el.get_text() if title_el else '')
    if not title:
        title = clean_text(full_text)
    
    # Photo
    img_el = card.select_one('img')
    photo = ''
    if img_el:
        photo = img_el.get('data-src') or img_el.get('src') or ''
        if photo and not photo.startswith('http'):
            photo = BASE_URL + photo
    
    # Extract details
    rooms = extract_rooms(full_text)
    area = extract_area(full_text)
    floor, total_floors = extract_floor(full_text)
    
    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=link, price=price, title=title or 'Mənzil',
        district='Bakı', rooms=rooms, area=area,
        floor=floor, total_floors=total_floors, photo=photo,
        property_type=detect_property_type(title),
        deal_type=deal_type,
    )


def _try_nextdata(html_text, deal_type='kiraye'):
    """Try to extract from __NEXT_DATA__ if available"""
    try:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_text, re.DOTALL)
        if not m:
            return []
        
        data = json.loads(m.group(1))
        
        # Search for items in various locations
        def find_items(obj, depth=0):
            if depth > 8:
                return []
            if isinstance(obj, dict):
                # Check for item arrays
                for key in ['items', 'ads', 'listings', 'data', 'results']:
                    if key in obj and isinstance(obj[key], list) and len(obj[key]) > 0:
                        return obj[key]
                # Recurse
                for v in obj.values():
                    result = find_items(v, depth + 1)
                    if result:
                        return result
            elif isinstance(obj, list) and len(obj) > 0:
                if isinstance(obj[0], dict) and 'id' in obj[0]:
                    return obj
            return []
        
        items_data = find_items(data)
        if not items_data:
            return []
        
        items = []
        for item in items_data[:50]:
            if not isinstance(item, dict) or not item.get('id'):
                continue
            
            raw_id = str(item.get('id', ''))
            price = clean_price(str(item.get('price', '') or item.get('price_value', '')))
            title = item.get('title', '') or 'Mənzil'
            
            # Photo
            photos = item.get('photos', [])
            photo = ''
            if photos and isinstance(photos, list):
                p = photos[0]
                photo = (p.get('url', '') if isinstance(p, dict) else str(p))
            
            # Link
            slug = item.get('url', '') or item.get('slug', '')
            link = f"{BASE_URL}/{slug}" if slug and not str(slug).startswith('http') else str(slug) or f"{BASE_URL}/items/{raw_id}"
            
            items.append(make_listing(
                SOURCE, SOURCE_NAME, raw_id,
                link=link, price=price, title=str(title)[:80],
                district='Bakı', rooms=item.get('rooms'), area=item.get('area'),
                photo=photo, property_type=detect_property_type(title),
                deal_type=deal_type,
            ))
        
        return items
    except Exception as e:
        return []
