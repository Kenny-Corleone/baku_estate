"""
EvTap — Lalafo.az parser
HTML kartoçkalarından elanları çıxarır
"""
from .base import (fetch, make_id, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_deal_type, make_listing)
import re

SOURCE = 'lalafo'
SOURCE_NAME = 'Lalafo.az'
BASE_URL = 'https://lalafo.az'

URLS = {
    'kiraye': 'https://lalafo.az/azerbaijan/nedvizhimost/arenda-kvartir?page={page}',
    'satis': 'https://lalafo.az/azerbaijan/nedvizhimost/prodazha-kvartir?page={page}',
}


def parse_lalafo(pages=2):
    results = []
    for deal_type, url_template in URLS.items():
        for page in range(1, pages + 1):
            url = url_template.format(page=page)
            print(f"  Yüklənir: {url}")
            soup = fetch(url)
            if not soup:
                continue

            cards = soup.select('[class*="LFAdTileHorizontal_adTileHorizontal"]')
            if not cards:
                cards = soup.select('.LFAdTileHorizontal')
            print(f"  Lalafo [{deal_type}] kartoçka: {len(cards)}")

            for card in cards:
                try:
                    r = _parse_card(card, deal_type)
                    if r:
                        results.append(r)
                except Exception as e:
                    print(f"  ⚠️ {e}")
    print(f"  Lalafo cəmi: {len(results)}")
    return results


def _parse_card(card, deal_type='kiraye'):
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = BASE_URL + href if href.startswith('/') else href

    m = re.search(r'[-_](\d{7,})', href)
    if not m:
        m = re.search(r'/(\d{5,})', href)
    if not m:
        raw_id = str(abs(hash(href)) % 10**10)
    else:
        raw_id = m.group(1)

    full_text = card.get_text(' ', strip=True)

    # Qiymət
    price_el = (card.select_one('[class*="weight-700"]') or
                card.select_one('[class*="LFSubHeading"]'))
    price = None
    if price_el:
        price = clean_price(re.sub(r'[^\d]', '', price_el.get_text()))
    if not price:
        pm = re.search(r'(\d[\d\s]{1,5})\s*AZN', full_text, re.IGNORECASE)
        if pm:
            price = clean_price(pm.group(1))

    # Başlıq
    title = ''
    for el in card.select('[class*="LFSubHeading"]'):
        t = clean_text(el.get_text())
        if t and not re.search(r'^\d+', t):
            title = t[:80]
            break

    # Rayon
    district = 'Bakı'
    for cap in card.select('[class*="LFCaption"]'):
        t = clean_text(cap.get_text())
        if t and len(t) > 3 and not re.search(r'AZN|\d{4,}', t, re.I):
            district = t[:60]
            break

    # Foto
    img_el = card.select_one('img')
    photo = ''
    if img_el:
        photo = img_el.get('data-src') or img_el.get('src') or ''
        if photo and not photo.startswith('http'):
            photo = BASE_URL + photo

    rooms = extract_rooms(full_text + ' ' + title)
    area = extract_area(full_text)
    floor, total = extract_floor(full_text)

    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=link, price=price, title=title or 'Mənzil',
        district=district, rooms=rooms, area=area,
        floor=floor, total_floors=total, photo=photo,
        deal_type=deal_type,
        property_type=detect_property_type(title + ' ' + full_text),
    )
