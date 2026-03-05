"""
EvTap — Villa.az parser
Villalar, evlər, kommersiya daşınmaz əmlak
"""
from .base import (fetch, fetch_rendered, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'villa'
SOURCE_NAME = 'Villa.az'
BASE_URL = 'https://villa.az'


def parse_villa(pages=2):
    results = []
    for page in range(1, pages + 1):
        url = f'{BASE_URL}/elanlar?page={page}'
        print(f"  Yüklənir: {url}")
        soup = fetch_rendered(url, timeout=60, wait_until='domcontentloaded')
        if not soup:
            continue

        # Villa listing pages are JS-rendered; build cards from listing links.
        candidates = []
        for a in soup.select('a[href]'):
            href = a.get('href', '')
            if not href:
                continue
            # Typical listing URLs end with -<id>
            if re.search(r'-\d{4,}$', href) and 'uploads' not in href:
                parent = a.find_parent(['div', 'li', 'article'])
                if parent:
                    candidates.append(parent)

        seen = set()
        cards = []
        for c in candidates:
            if id(c) not in seen:
                seen.add(id(c))
                cards.append(c)
        print(f"  Villa kartoçka: {len(cards)}")

        for card in cards:
            try:
                r = _parse_card(card)
                if r:
                    results.append(r)
            except Exception as e:
                print(f"  ⚠️ {e}")
    print(f"  Villa cəmi: {len(results)}")
    return results


def _parse_card(card):
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = href if href.startswith('http') else BASE_URL + href

    m = re.search(r'-(\d{4,})$', href)
    if not m:
        m = re.search(r'/(\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)

    full_text = card.get_text(' ', strip=True)
    price_el = card.select_one('.price') or card.select_one('[class*="price"]')
    price = clean_price(price_el.get_text()) if price_el else None

    title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('.title')
    title = clean_text(title_el.get_text() if title_el else '')
    district = detect_district(full_text)
    deal_type = 'kiraye' if any(w in full_text.lower() for w in ['kirayə', 'icarə', 'rent']) else 'satis'

    img_el = card.select_one('img')
    photo = ''
    if img_el:
        photo = img_el.get('data-src') or img_el.get('src') or ''
        if photo and not photo.startswith('http'):
            photo = BASE_URL + photo

    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=link, price=price, title=title or 'Villa',
        district=district, rooms=extract_rooms(full_text), area=extract_area(full_text),
        floor=extract_floor(full_text)[0], total_floors=extract_floor(full_text)[1], photo=photo,
        deal_type=deal_type,
        property_type=detect_property_type(title + ' ' + full_text) or 'ev_villa',
    )
