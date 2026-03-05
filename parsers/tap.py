"""
EvTap — Tap.az parser
API və HTML-dən elanları çıxarır
"""
import requests, random, re, time, json
from .base import (make_id, clean_price, clean_text, extract_rooms,
                   extract_area, detect_property_type, detect_deal_type, make_listing)

SOURCE = 'tap'
SOURCE_NAME = 'Tap.az'
BASE_URL = 'https://tap.az'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

# category_id=241 = mənzillər, params[740]=3724 = kirayə, 3723 = satış
API_ENDPOINTS_RENT = [
    'https://tap.az/api/v2/ads?category_id=241&params[740]=3724&page={page}&per_page=20',
    'https://tap.az/api/v1/ads?category_id=241&params[740]=3724&page={page}',
]
API_ENDPOINTS_SALE = [
    'https://tap.az/api/v2/ads?category_id=241&params[740]=3723&page={page}&per_page=20',
    'https://tap.az/api/v1/ads?category_id=241&params[740]=3723&page={page}',
]

HTML_URLS = {
    'kiraye': 'https://tap.az/elanlar/dasinmaz-emlak/menziller?p%5B740%5D=3724&page={page}',
    'satis': 'https://tap.az/elanlar/dasinmaz-emlak/menziller?p%5B740%5D=3723&page={page}',
}


def _session(json_mode=False):
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept': 'application/json, text/plain, */*' if json_mode else 'text/html,*/*',
        'Accept-Language': 'az,ru;q=0.9,en;q=0.8',
        'Referer': 'https://tap.az/elanlar/dasinmaz-emlak/menziller',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://tap.az',
    })
    return s


def parse_tap(pages=2):
    results = []
    for deal_type, endpoints in [('kiraye', API_ENDPOINTS_RENT), ('satis', API_ENDPOINTS_SALE)]:
        for page in range(1, pages + 1):
            items = _try_api(page, endpoints, deal_type) or _try_html_extract(page, deal_type)
            if items:
                results.extend(items)
                print(f"  Tap [{deal_type}] səhifə {page}: {len(items)} elan")
            else:
                print(f"  Tap [{deal_type}] səhifə {page}: 0 elan")
            time.sleep(random.uniform(1, 2))
    print(f"  Tap cəmi: {len(results)}")
    return results


def _try_api(page, endpoints, deal_type):
    for endpoint in endpoints:
        url = endpoint.format(page=page)
        try:
            s = _session(json_mode=True)
            time.sleep(random.uniform(0.5, 1.5))
            resp = s.get(url, timeout=15)
            print(f"    [API {resp.status_code}] {url.split('?')[0]}")
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    items = (data.get('data') or data.get('ads') or
                             data.get('items') or data.get('results') or [])
                    if items and len(items) > 0:
                        print(f"    ✅ API işləyir! {len(items)} elan")
                        return [_map(i, deal_type) for i in items if i]
                except:
                    pass
        except Exception as e:
            print(f"    API xəta: {e}")
    return None


def _try_html_extract(page, deal_type):
    url = HTML_URLS.get(deal_type, HTML_URLS['kiraye']).format(page=page)
    try:
        s = _session()
        time.sleep(random.uniform(1.5, 3))
        resp = s.get(url, timeout=20)
        if resp.status_code != 200:
            return None
        resp.encoding = resp.apparent_encoding or 'utf-8'
        text = resp.text

        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            items = _dig_for_ads(data)
            if items:
                return [_map(i, deal_type) for i in items]

        json_arrays = re.findall(
            r'\[(\{"id":\d+,"title":"[^"]{5,}"[^}]{10,}"price"[^]]{20,})\]',
            text, re.DOTALL
        )
        for arr_str in json_arrays[:3]:
            try:
                arr = json.loads('[' + arr_str + ']')
                if len(arr) > 3:
                    return [_map(i, deal_type) for i in arr]
            except:
                pass

        ad_blocks = re.findall(
            r'"id":(\d+),"title":"([^"]+)"[^}]*"price":\{"value":(\d+)',
            text
        )
        if ad_blocks:
            return [_minimal(bid, title, price, deal_type) for bid, title, price in ad_blocks[:20]]

    except Exception as e:
        print(f"    Tap HTML xəta: {e}")
    return None


def _dig_for_ads(data, depth=0):
    if depth > 5:
        return []
    if isinstance(data, list) and len(data) > 3:
        if isinstance(data[0], dict) and 'id' in data[0] and 'price' in data[0]:
            return data[:50]
    if isinstance(data, dict):
        for key in ['ads', 'items', 'data', 'results', 'listings', 'products', 'adsList']:
            v = data.get(key)
            if v and isinstance(v, list) and len(v) > 2:
                if isinstance(v[0], dict) and 'id' in v[0]:
                    return v
        for v in data.values():
            if isinstance(v, (dict, list)):
                r = _dig_for_ads(v, depth + 1)
                if r and len(r) > 2:
                    return r
    return []


def _map(item, deal_type='kiraye'):
    if not isinstance(item, dict):
        return None
    raw_id = str(item.get('id', ''))
    if not raw_id:
        return None

    price_data = item.get('price', {})
    if isinstance(price_data, dict):
        price = clean_price(price_data.get('value') or price_data.get('amount'))
    else:
        price = clean_price(price_data)

    city = item.get('city', {})
    district = city.get('name', 'Bakı') if isinstance(city, dict) else str(city or 'Bakı')

    photos = item.get('photos', [])
    photo = ''
    if photos and isinstance(photos, list):
        p = photos[0]
        photo = (p.get('url', '') if isinstance(p, dict) else str(p))

    title = item.get('title', '') or item.get('name', '')
    link = item.get('url', '') or item.get('link', '')
    if link and not link.startswith('http'):
        link = BASE_URL + link
    if not link:
        link = f'{BASE_URL}/elanlar/{raw_id}'

    params = item.get('params', []) or []
    rooms, area = None, None
    for p in params:
        if not isinstance(p, dict):
            continue
        name = str(p.get('name', '')).lower()
        val = str(p.get('value', ''))
        if 'otaq' in name or 'room' in name:
            try:
                rooms = int(re.sub(r'[^\d]', '', val))
            except:
                pass
        if 'sahə' in name or 'area' in name or 'm²' in name:
            try:
                area = float(re.sub(r'[^\d.]', '', val))
            except:
                pass

    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=link, price=price, title=str(title)[:80] or 'Mənzil',
        district=str(district)[:50] or 'Bakı', rooms=rooms, area=area,
        photo=photo, deal_type=deal_type,
        property_type=detect_property_type(title),
    )


def _minimal(bid, title, price, deal_type='kiraye'):
    return make_listing(
        SOURCE, SOURCE_NAME, bid,
        link=f'{BASE_URL}/elanlar/{bid}', price=int(price),
        title=title[:80], district='Bakı', rooms=extract_rooms(title),
        deal_type=deal_type, property_type=detect_property_type(title),
    )
