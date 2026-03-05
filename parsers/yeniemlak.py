"""
EvTap — YeniEmlak.az parser
"""
from .base import (fetch, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'yeniemlak'
SOURCE_NAME = 'YeniEmlak.az'
BASE_URL = 'https://yeniemlak.az'


def parse_yeniemlak(pages=2):
    results = []
    for page in range(1, pages + 1):
        url = f'{BASE_URL}/?page={page}'
        print(f"  Yüklənir: {url}")
        soup = fetch(url)
        if not soup:
            continue

        cards = (soup.select('.item') or soup.select('.ad') or
                 soup.select('.listing') or soup.select('article'))
        print(f"  YeniEmlak kartoçka: {len(cards)}")

        for card in cards:
            try:
                r = _parse_card(card)
                if r:
                    results.append(r)
            except Exception as e:
                print(f"  ⚠️ {e}")
    print(f"  YeniEmlak cəmi: {len(results)}")
    return results


def _parse_card(card):
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = href if href.startswith('http') else BASE_URL + href

    m = re.search(r'/(\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)

    full_text = card.get_text(' ', strip=True)
    price_el = card.select_one('.price') or card.select_one('[class*="price"]')
    price = clean_price(price_el.get_text()) if price_el else None
    if not price:
        pm = re.search(r'(\d[\d\s.,]{0,10})\s*(?:AZN|₼|manat)', full_text, re.IGNORECASE)
        if pm:
            price = clean_price(pm.group(1))

    title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('.title')
    title = clean_text(title_el.get_text() if title_el else '')
    district = detect_district(full_text)
    deal_type = 'satis' if any(w in full_text.lower() for w in ['satış', 'satılır', 'sale']) else 'kiraye'

    img_el = card.select_one('img')
    photo = ''
    if img_el:
        photo = img_el.get('data-src') or img_el.get('src') or ''
        if photo and not photo.startswith('http'):
            photo = BASE_URL + photo

    rooms = extract_rooms(full_text)
    area = extract_area(full_text)
    floor, total = extract_floor(full_text)

    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=link, price=price, title=title or 'Elan',
        district=district, rooms=rooms, area=area,
        floor=floor, total_floors=total, photo=photo,
        deal_type=deal_type,
        property_type=detect_property_type(title + ' ' + full_text),
    )
