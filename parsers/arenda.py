"""
EvTap — Arenda.az parser
HTML kartoçkalarından elanları çıxarır
"""
from .base import (fetch, make_id, clean_price, clean_text,
                   extract_rooms, extract_area, extract_floor,
                   detect_property_type, detect_district, make_listing)
import re
from bs4 import Comment

SOURCE = 'arenda'
SOURCE_NAME = 'Arenda.az'
BASE_URL = 'https://arenda.az'


def parse_arenda(pages=2):
    results = []
    for page in range(1, pages + 1):
        url = f'https://arenda.az/kiraye/menzil?page={page}' if page > 1 else 'https://arenda.az/kiraye/menzil'
        print(f"  Yüklənir: {url}")
        soup = fetch(url)
        if not soup:
            continue

        cards = []
        for cls in ['xususi_elan_box', 'new_elan_box']:
            cards.extend(soup.select(f'.{cls}'))

        if not cards:
            seen = set()
            for t in soup.select('.elan_property_title'):
                parent = t.find_parent(['div', 'li', 'article'])
                if parent and id(parent) not in seen:
                    seen.add(id(parent))
                    cards.append(parent)

        print(f"  Arenda kartoçka: {len(cards)}")

        for card in cards:
            try:
                r = _parse_card(card, soup)
                if r:
                    results.append(r)
            except Exception as e:
                print(f"  ⚠️ {e}")

    print(f"  Arenda cəmi: {len(results)}")
    return results


def _parse_card(card, full_soup):
    link_el = card.select_one('a[href]')
    if not link_el:
        return None
    href = link_el.get('href', '')
    if not href:
        return None
    link = BASE_URL + href if href.startswith('/') else href

    m = re.search(r'/(\d{4,})', href)
    raw_id = m.group(1) if m else str(abs(hash(href)) % 10**10)

    full_text = card.get_text(' ', strip=True)
    
    # Qiymət — HTML-də şərhlərdə və ya mətnlərdə
    price = None
    
    # Try visible price elements first
    for price_cls in ['.elan_price', '[class*="price"]', '.price', '[class*="qiymet"]']:
        price_el = card.select_one(price_cls)
        if price_el:
            price_text = price_el.get_text()
            price = clean_price(price_text)
            if price:
                break
    
    # Try from full text
    if not price:
        price_m = re.search(r'(\d[\d\s]{2,})\s*(?:AZN|₼|manat)', full_text, re.IGNORECASE)
        if price_m:
            price = clean_price(price_m.group(1))
    
    # Try HTML source
    if not price:
        card_html = str(card)
        price_m = re.search(r"(?:elan_price|price|qiymet)['\">]*\s*>?\s*(\d[\d\s]*)\s*(?:AZN|₼)", card_html, re.IGNORECASE)
        if price_m:
            price = clean_price(price_m.group(1))

    # Try comments
    if not price:
        for comment in card.find_all(string=lambda t: isinstance(t, Comment)):
            cm = re.search(r'(\d[\d\s]+)\s*(?:AZN|₼)', str(comment), re.IGNORECASE)
            if cm:
                price = clean_price(cm.group(1))
                break

    # Başlıq
    title_el = (card.select_one('.elan_property_title') or
                card.select_one('[class*="title"]') or
                card.select_one('h2') or card.select_one('h3'))
    title = clean_text(title_el.get_text() if title_el else '')

    # Rayon
    district_el = card.select_one('[class*="location"]') or card.select_one('[class*="address"]')
    if district_el:
        from .base import detect_district
        district = detect_district(district_el.get_text())
    else:
        from .base import detect_district
        district = detect_district(full_text)

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
        link=link, price=price, title=title or 'Mənzil kirayəsi',
        district=district, rooms=rooms, area=area,
        floor=floor, total_floors=total, photo=photo,
        deal_type='kiraye',
        property_type=detect_property_type(title + ' ' + full_text),
    )
