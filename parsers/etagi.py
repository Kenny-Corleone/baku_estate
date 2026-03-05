"""
EvTap — Etagi.com (Bakı) parser
"""
from .base import (fetch, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'etagi'
SOURCE_NAME = 'Etagi.com'
BASE_URL = 'https://baku.etagi.com'


def parse_etagi(pages=2):
    results = []
    for page in range(1, pages + 1):
        url = f'{BASE_URL}/realty/?page={page}'
        print(f"  Yüklənir: {url}")
        soup = fetch(url)
        if not soup:
            continue

        cards = (soup.select('.templates-object-card') or
                 soup.select('[class*="OfferItem"]') or
                 soup.select('[class*="property-card"]') or
                 soup.select('article') or soup.select('.item'))
        print(f"  Etagi kartoçka: {len(cards)}")

        for card in cards:
            try:
                r = _parse_card(card)
                if r:
                    results.append(r)
            except Exception as e:
                print(f"  ⚠️ {e}")
    print(f"  Etagi cəmi: {len(results)}")
    return results


def _parse_card(card):
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = href if href.startswith('http') else BASE_URL + href

    m = re.search(r'/realty/(\d+)/', href)
    if not m:
        m = re.search(r'/(\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)

    full_text = card.get_text(' ', strip=True)
    price = None
    price_el = card.select_one('[class*="price"]') or card.select_one('.price')
    if price_el:
        price = clean_price(price_el.get_text())
    if not price:
        pm = re.search(r'(\d[\d\s.,]{0,12})\s*(?:AZN|₼|\$|€)', full_text)
        if pm:
            price = clean_price(pm.group(1))

    title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('[class*="title"]')
    title = clean_text(title_el.get_text() if title_el else '')
    if not title:
        title = clean_text(full_text)[:80]
    district = detect_district(full_text)
    deal_type = 'kiraye' if any(w in full_text.lower() for w in ['аренда', 'kirayə', 'rent']) else 'satis'

    img_el = card.select_one('img')
    photo = ''
    if img_el:
        photo = img_el.get('data-src') or img_el.get('src') or ''
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
