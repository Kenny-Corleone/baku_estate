"""
EvTap — Tap.az parser
API və HTML-dən elanları çıxarır
"""
import requests, random, re, time, json
from bs4 import BeautifulSoup
from .base import (make_id, clean_price, clean_text, extract_rooms,
                   extract_area, extract_floor, detect_property_type, detect_deal_type, make_listing, fetch_rendered)

SOURCE = 'tap'
SOURCE_NAME = 'Tap.az'
BASE_URL = 'https://tap.az'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

HTML_URLS = {
    'kiraye': 'https://tap.az/elanlar/dasinmaz-emlak/menziller?page={page}',
    'satis': 'https://tap.az/elanlar/dasinmaz-emlak/menziller?page={page}',
}


def _session(json_mode=False):
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept': 'application/json, text/plain, */*' if json_mode else 'text/html,*/*',
        'Accept-Language': 'az,ru;q=0.9,en;q=0.8',
        'Referer': 'https://tap.az/elanlar/dasinmaz-emlak/menziller',
    })
    return s


def parse_tap(pages=2):
    results = []
    for deal_type in ['kiraye', 'satis']:
        for page in range(1, pages + 1):
            items = _fetch_html(page, deal_type)
            if items:
                results.extend(items)
                print(f"  Tap [{deal_type}] səhifə {page}: {len(items)} elan")
            else:
                print(f"  Tap [{deal_type}] səhifə {page}: 0 elan")
            time.sleep(random.uniform(1, 2))
    print(f"  Tap cəmi: {len(results)}")
    return results


def _fetch_html(page, deal_type):
    """Fetch from rendered HTML page (Playwright)"""
    url = HTML_URLS.get(deal_type, HTML_URLS['kiraye']).format(page=page)
    try:
        soup = fetch_rendered(url, timeout=45, wait_until='domcontentloaded')
        if not soup:
            return []

        html_text = str(soup).lower()
        if any(x in html_text for x in ['cloudflare', 'captcha', 'cf-chl', 'turnstile']):
            print('    Tap: blocked by Cloudflare/captcha')
            return []

        # Find listing cards
        cards = (soup.select('[class*="products-i"]') or
                 soup.select('[class*="lot-"]') or
                 soup.select('article') or
                 soup.select('[data-item-id]'))
        if not cards:
            # fallback: any anchor with /elanlar/<id>
            cards = [a.find_parent(['div', 'li', 'article']) for a in soup.select('a[href]')
                     if re.search(r'/elanlar/\d+', a.get('href', ''))]
            cards = [c for c in cards if c]

        items = []
        for card in cards:
            try:
                item = _parse_card(card, deal_type)
                if item:
                    items.append(item)
            except:
                pass
        
        return items
    except Exception as e:
        print(f"    Tap HTML xəta: {e}")
        return []


def _parse_card(card, deal_type='kiraye'):
    """Parse a single listing card"""
    # Get link
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = href if href.startswith('http') else BASE_URL + href
    
    # Extract ID
    m = re.search(r'/elanlar/(\d+)', href)
    if not m:
        m = re.search(r'[-_](\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)
    
    full_text = card.get_text(' ', strip=True)
    
    # Price
    price_el = card.select_one('[class*="price"]')
    price = clean_price(price_el.get_text()) if price_el else None
    
    # Title
    title_el = card.select_one('[class*="title"]') or card.select_one('h2') or card.select_one('h3')
    title = clean_text(title_el.get_text() if title_el else '')
    
    # Photo
    img_el = card.select_one('img')
    photo = ''
    if img_el:
        photo = img_el.get('data-src') or img_el.get('src') or ''
        if photo and not photo.startswith('http'):
            photo = BASE_URL + photo
    
    # Extract details
    rooms = extract_rooms(full_text + ' ' + title)
    area = extract_area(full_text)
    floor, total_floors = extract_floor(full_text)
    
    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=link, price=price, title=title or 'Mənzil',
        district='Bakı', rooms=rooms, area=area,
        floor=floor, total_floors=total_floors, photo=photo,
        deal_type=deal_type,
        property_type=detect_property_type(title),
    )
