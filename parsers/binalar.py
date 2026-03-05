"""
EvTap — Binalar.az parser
"""
from .base import (fetch, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'binalar'
SOURCE_NAME = 'Binalar.az'
BASE_URL = 'https://binalar.az'

URLS = {
    'satis': 'https://binalar.az/?page={page}',
    'kiraye': 'https://binalar.az/?page={page}',
}


def parse_binalar(pages=2):
    results = []
    for deal_type, url_template in URLS.items():
        for page in range(1, pages + 1):
            url = url_template.format(page=page)
            print(f"  Yüklənir: {url}")
            soup = fetch(url)
            if not soup:
                continue

            cards = (soup.select('.item') or soup.select('.listing') or
                     soup.select('article') or soup.select('.property-item'))
            if not cards:
                candidates = []
                for a in soup.select('a[href]'):
                    href = a.get('href', '')
                    if href and href.startswith('/') and re.search(r'-\d{4,}$', href):
                        parent = a.find_parent(['div', 'li', 'article'])
                        candidates.append(parent or a)
                seen = set()
                cards = []
                for c in candidates:
                    if id(c) not in seen:
                        seen.add(id(c))
                        cards.append(c)
            print(f"  Binalar [{deal_type}] kartoçka: {len(cards)}")

            for card in cards:
                try:
                    r = _parse_card(card, deal_type)
                    if r:
                        results.append(r)
                except Exception as e:
                    print(f"  ⚠️ {e}")
    print(f"  Binalar cəmi: {len(results)}")
    return results


def _parse_card(card, deal_type='satis'):
    if getattr(card, 'name', None) == 'a':
        link_el = card
    else:
        link_el = card.select_one('a[href^="/"][href]') or card.select_one('a[href]')
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
    price = None
    price_el = card.select_one('.price') or card.select_one('[class*="price"]')
    if price_el:
        price = clean_price(price_el.get_text())
    if not price:
        pm = re.search(r'(\d[\d\s.,]{0,12})\s*(?:AZN|₼|manat)', full_text, re.IGNORECASE)
        if pm:
            price = clean_price(pm.group(1))

    title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('.title') or card.select_one('.name')
    title = clean_text(title_el.get_text() if title_el else '')
    if not title and getattr(link_el, 'get_text', None):
        title = clean_text(link_el.get_text(' ', strip=True))
    if title:
        title = re.sub(r'^\s*\d[\d\s.,]*\s*(?:AZN|₼)\s*/?\s*', '', title, flags=re.IGNORECASE)[:80]
    district = detect_district(full_text)

    img_el = None
    for cand in card.select('img'):
        src = cand.get('data-src') or cand.get('src') or ''
        if not src:
            continue
        if 'heart.svg' in src or 'img/heart' in src:
            continue
        img_el = cand
        break
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
