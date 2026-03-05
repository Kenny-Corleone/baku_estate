"""
EvTap — Tikili.az parser
"""
from .base import (fetch, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'tikili'
SOURCE_NAME = 'Tikili.az'
BASE_URL = 'https://tikili.az'

URLS = {
    'satis': 'https://tikili.az/ru/sale?page={page}',
    'kiraye': 'https://tikili.az/ru/rent?page={page}',
}


def parse_tikili(pages=2):
    results = []
    for deal_type, url_template in URLS.items():
        for page in range(1, pages + 1):
            url = url_template.format(page=page)
            print(f"  Yüklənir: {url}")
            soup = fetch(url)
            if not soup:
                continue

            cards = (soup.select('div.ad-card') or
                     soup.select('article.property-card') or
                     soup.select('.listing-item') or
                     soup.select('.item'))
            print(f"  Tikili [{deal_type}] kartoçka: {len(cards)}")

            for card in cards:
                try:
                    r = _parse_card(card, deal_type)
                    if r:
                        results.append(r)
                except Exception as e:
                    print(f"  ⚠️ {e}")
    print(f"  Tikili cəmi: {len(results)}")
    return results


def _parse_card(card, deal_type='satis'):
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = href if href.startswith('http') else BASE_URL + href

    m = re.search(r'/(\d{4,})', href)
    if not m:
        m = re.search(r'[-_](\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)

    full_text = card.get_text(' ', strip=True)

    price_el = card.select_one('.price') or card.select_one('.card-price') or card.select_one('[class*="price"]')
    price = clean_price(price_el.get_text()) if price_el else None
    if not price:
        pm = re.search(r'(\d[\d\s.,]{0,10})\s*(?:AZN|₼|manat)', full_text, re.IGNORECASE)
        if pm:
            price = clean_price(pm.group(1))

    title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('.card-title') or card.select_one('[class*="title"]')
    title = clean_text(title_el.get_text() if title_el else '')

    addr_el = card.select_one('.address') or card.select_one('.location') or card.select_one('[class*="address"]')
    district = detect_district(addr_el.get_text() if addr_el else full_text)

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
