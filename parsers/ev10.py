"""
EvTap — Ev10.az parser
"""
from .base import (fetch, make_id, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'ev10'
SOURCE_NAME = 'Ev10.az'
BASE_URL = 'https://ev10.az'

URLS = {
    'satis': 'https://ev10.az/elanlar/dasinmaz-emlak/menzil-satilir?page={page}',
    'kiraye': 'https://ev10.az/elanlar/dasinmaz-emlak/menzil-kiraye?page={page}',
}


def parse_ev10(pages=2):
    results = []
    for deal_type, url_template in URLS.items():
        for page in range(1, pages + 1):
            url = url_template.format(page=page)
            print(f"  Yüklənir: {url}")
            soup = fetch(url)
            if not soup:
                continue

            cards = soup.select('.products_item') or soup.select('.item') or soup.select('[class*="card"]')
            print(f"  Ev10 [{deal_type}] kartoçka: {len(cards)}")

            for card in cards:
                try:
                    r = _parse_card(card, deal_type)
                    if r:
                        results.append(r)
                except Exception as e:
                    print(f"  ⚠️ {e}")
    print(f"  Ev10 cəmi: {len(results)}")
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
    if not m:
        raw_id = str(abs(hash(href)) % 10**10)
    else:
        raw_id = m.group(1)

    full_text = card.get_text(' ', strip=True)

    # Qiymət
    price = None
    price_el = card.select_one('.price') or card.select_one('[class*="price"]')
    if price_el:
        price = clean_price(price_el.get_text())
    if not price:
        pm = re.search(r'(\d[\d\s.,]{0,10})\s*(?:AZN|₼|manat)', full_text, re.IGNORECASE)
        if pm:
            price = clean_price(pm.group(1))

    # Başlıq
    title_el = card.select_one('[class*="title"]') or card.select_one('h2') or card.select_one('h3')
    title = clean_text(title_el.get_text() if title_el else '')

    # Rayon
    district = detect_district(full_text)

    # Foto
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
