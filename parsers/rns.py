"""
EvTap — RNS.az parser
Daşınmaz əmlak agentliyi
"""
from .base import (fetch, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re

SOURCE = 'rns'
SOURCE_NAME = 'RNS.az'
BASE_URL = 'https://rns.az'


def parse_rns(pages=2):
    results = []
    for page in range(1, pages + 1):
        url = f'{BASE_URL}/elanlar?page={page}'
        print(f"  Yüklənir: {url}")
        soup = fetch(url)
        if not soup:
            continue

        candidates = []
        for a in soup.select('a[href]'):
            href = a.get('href', '')
            if '/property/' in href and '/agent/' not in href:
                parent = a.find_parent(['article', 'div', 'li'])
                candidates.append(parent or a)
        seen = set()
        cards = []
        for c in candidates:
            if id(c) not in seen:
                seen.add(id(c))
                cards.append(c)
        print(f"  RNS kartoçka: {len(cards)}")

        for card in cards:
            try:
                r = _parse_card(card)
                if r:
                    results.append(r)
            except Exception as e:
                print(f"  ⚠️ {e}")
    print(f"  RNS cəmi: {len(results)}")
    return results


def _parse_card(card):
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    if '/property/' not in href or '/agent/' in href:
        return None
    link = href if href.startswith('http') else BASE_URL + href

    full_text = card.get_text(' ', strip=True)
    low = full_text.lower()
    if any(w in low for w in ['лучшие предложения', 'последние обновления', 'read more', 'blog']):
        return None

    m = re.search(r'/(\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)

    price_el = card.select_one('.price') or card.select_one('[class*="price"]')
    price = clean_price(price_el.get_text()) if price_el else None

    title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('.title')
    title = clean_text(title_el.get_text() if title_el else '')
    if not title:
        title = clean_text(link_el.get_text(' ', strip=True))
    # Clean common non-title prefixes
    if title:
        title = re.sub(r'^(vip\s+)?(лучшие предложения|последние обновления)\s*', '', title, flags=re.IGNORECASE).strip()
        title = title[:80]
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
        link=link, price=price, title=title or 'Elan',
        district=district, rooms=extract_rooms(full_text), area=extract_area(full_text),
        floor=extract_floor(full_text)[0], total_floors=extract_floor(full_text)[1], photo=photo,
        deal_type=deal_type,
        property_type=detect_property_type(title + ' ' + full_text),
    )
