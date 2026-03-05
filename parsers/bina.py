"""
EvTap — Bina.az parser
__NEXT_DATA__ apolloState-dən elanları çıxarır
"""
import requests, random, re, time, json
from .base import make_id, clean_price, clean_text, detect_property_type, detect_deal_type, make_listing

SOURCE = 'bina'
SOURCE_NAME = 'Bina.az'
BASE_URL = 'https://bina.az'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

# Kirayə və satış üçün ayrı URL-lər
URLS = {
    'kiraye': 'https://bina.az/baki/kiraye/menziller?page={page}',
    'satis': 'https://bina.az/baki/alqi-satqi/menziller?page={page}',
}


def parse_bina(pages=2):
    results = []
    for deal_type, url_template in URLS.items():
        for page in range(1, pages + 1):
            url = url_template.format(page=page)
            print(f"  Yüklənir: {url}")
            items = _fetch_nextdata(url, deal_type)
            print(f"  Bina [{deal_type}] səhifə {page}: {len(items)} elan")
            results.extend(items)
            time.sleep(random.uniform(1.5, 2.5))
    print(f"  Bina cəmi: {len(results)}")
    return results


def _fetch_nextdata(url, deal_type='kiraye'):
    try:
        s = requests.Session()
        s.headers.update({
            'User-Agent': UA,
            'Accept': 'text/html,*/*',
            'Accept-Language': 'az,ru;q=0.9',
        })
        resp = s.get(url, timeout=20)
        if resp.status_code != 200:
            return []
        resp.encoding = resp.apparent_encoding or 'utf-8'
        text = resp.text

        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if not m:
            print(f"  ❌ __NEXT_DATA__ tapılmadı")
            return []

        data = json.loads(m.group(1))

        apollo = data.get('props', {}).get('initialState', {}).get('apolloState', {})
        if not apollo:
            apollo = data.get('apolloState', {})

        items = []
        for key, val in apollo.items():
            if not (key.startswith('Item:') and re.match(r'Item:\d+', key)):
                continue
            if not isinstance(val, dict):
                continue
            if not val.get('price'):
                continue

            raw_id = key.replace('Item:', '')
            price = clean_price(str(val.get('price', '') or val.get('price_value', '')))

            # Foto
            photo = ''
            photos = val.get('photos', [])
            if photos and isinstance(photos, list):
                p = photos[0]
                if isinstance(p, dict):
                    photo = p.get('url', '') or p.get('thumbnail', '')
                else:
                    photo = str(p)

            # Parametrlər
            rooms = None
            area = None
            floor = None
            total_floors = None
            params = val.get('params', []) or []
            for p in params:
                if not isinstance(p, dict):
                    continue
                pid = str(p.get('id', ''))
                pval = str(p.get('value', ''))
                if pid in ('1', 'room', 'rooms'):
                    try:
                        rooms = int(re.sub(r'[^\d]', '', pval))
                    except:
                        pass
                elif pid in ('2', 'area', 'sahə'):
                    try:
                        area = float(re.sub(r'[^\d.]', '', pval))
                    except:
                        pass
                elif pid in ('4', 'floor', 'mərtəbə'):
                    fm = re.search(r'(\d+)\s*/\s*(\d+)', pval)
                    if fm:
                        floor, total_floors = int(fm.group(1)), int(fm.group(2))

            # Rayon
            city_ref = val.get('city', {})
            if isinstance(city_ref, dict):
                district = city_ref.get('name', 'Bakı')
            else:
                district = str(city_ref) if city_ref else 'Bakı'

            district2 = val.get('district', {})
            if isinstance(district2, dict) and district2.get('name'):
                district = district2['name']

            title = val.get('title', '') or (f"{rooms}-otaqlı mənzil" if rooms else 'Mənzil')
            slug = val.get('url', '') or val.get('slug', '')
            link = f"{BASE_URL}/{slug}" if slug and not str(slug).startswith('http') else str(slug) or f"{BASE_URL}/items/{raw_id}"

            prop_type = detect_property_type(str(title) + ' ' + str(val.get('category', '')))

            items.append(make_listing(
                SOURCE, SOURCE_NAME, raw_id,
                link=link, price=price, title=str(title)[:80],
                district=str(district)[:50] or 'Bakı',
                rooms=rooms, area=area, floor=floor, total_floors=total_floors,
                photo=photo, property_type=prop_type, deal_type=deal_type,
            ))

        # apolloState-dən heç nə tapılmadısa — pageProps-a bax
        if not items:
            page_props = data.get('props', {}).get('initialProps', {}).get('pageProps', {})
            for key in ['items', 'listings', 'data', 'ads']:
                lst = page_props.get(key, [])
                if lst and isinstance(lst, list):
                    print(f"  pageProps.{key}-da tapıldı: {len(lst)}")
                    for item in lst:
                        r = _map_item(item, deal_type)
                        if r:
                            items.append(r)
                    break

        return items

    except Exception as e:
        print(f"  ❌ Bina xəta: {e}")
        import traceback
        traceback.print_exc()
        return []


def _map_item(item, deal_type='kiraye'):
    if not isinstance(item, dict):
        return None
    raw_id = str(item.get('id', ''))
    if not raw_id:
        return None
    price = clean_price(str(item.get('price', '') or ''))
    photo = ''
    photos = item.get('photos', [])
    if photos and isinstance(photos, list):
        p = photos[0]
        photo = p.get('url', '') if isinstance(p, dict) else str(p)
    return make_listing(
        SOURCE, SOURCE_NAME, raw_id,
        link=f"{BASE_URL}/items/{raw_id}", price=price,
        title=item.get('title', 'Mənzil')[:80], district='Bakı',
        rooms=item.get('rooms'), area=item.get('area'),
        property_type=detect_property_type(item.get('title', '')),
        deal_type=deal_type, photo=photo,
    )
