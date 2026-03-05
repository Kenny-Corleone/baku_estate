"""
EvTap — RahatEmlak.az parser
"""
from .base import (fetch, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'rahatemlak'
SOURCE_NAME = 'RahatEmlak.az'
BASE_URL = 'https://rahatemlak.az'


def parse_rahatemlak(pages=2):
    results = []
    for page in range(1, pages + 1):
        url = f'{BASE_URL}/?page={page}'
        print(f"  Yüklənir: {url}")
        soup = fetch(url)
        if not soup:
            continue

        cards = (soup.select('.property-card') or
                 soup.select('.item') or soup.select('.ad-item') or
                 soup.select('.listing') or soup.select('article'))
        print(f"  RahatEmlak kartoçka: {len(cards)}")

        for card in cards:
            try:
                r = _parse_card(card)
                if r:
                    results.append(r)
            except Exception as e:
                print(f"  ⚠️ {e}")
    print(f"  RahatEmlak cəmi: {len(results)}")
    return results


def _parse_card(card):
    # RahatEmlak list cards often do not contain an <a>; use image path to derive id.
    raw_id = None
    link = ''

    img_el = card.select_one('img')
    img_url = ''
    if img_el:
        img_url = img_el.get('data-src') or img_el.get('src') or ''
        m = re.search(r'/images/property/(\d+)/', img_url)
        if m:
            raw_id = m.group(1)

    if raw_id:
        link = f'{BASE_URL}/elan/{raw_id}'
    else:
        # fallback id
        raw_id = str(abs(hash(card.get_text(' ', strip=True))) % 10**10)
        link = BASE_URL

    full_text = card.get_text(' ', strip=True)

    price = None
    price_el = card.select_one('.price') or card.select_one('[class*="price"]')
    if price_el:
        price = clean_price(price_el.get_text())
    if not price:
        pm = re.search(r'(\d[\d\s.,]{0,12})\s*(?:AZN|₼|manat)', full_text, re.IGNORECASE)
        if pm:
            price = clean_price(pm.group(1))

    title = ''
    title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('.title')
    if title_el:
        title = clean_text(title_el.get_text())
    if not title and img_el and img_el.get('alt'):
        title = clean_text(img_el.get('alt'))
    if not title:
        title = clean_text(full_text)[:80]
    district = detect_district(full_text)
    deal_type = 'kiraye' if any(w in full_text.lower() for w in ['kirayə', 'icarə', 'rent']) else 'satis'

    photo = ''
    if img_url:
        photo = img_url
        if photo and not photo.startswith('http'):
            photo = BASE_URL + photo

    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=link, price=price, title=title or 'Elan',
        district=district, rooms=extract_rooms(full_text), area=extract_area(full_text),
        floor=extract_floor(full_text)[0], total_floors=extract_floor(full_text)[1], photo=photo,
        deal_type=deal_type,
        property_type=detect_property_type(title + ' ' + full_text),
    )
