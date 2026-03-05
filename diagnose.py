"""
Диагностика v2 — python diagnose.py
"""
import sys, os, re, requests, random, json
sys.path.insert(0, os.path.dirname(__file__))
from bs4 import BeautifulSoup

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

def get(url):
    s = requests.Session()
    s.headers.update({'User-Agent': UA, 'Accept': 'text/html,*/*', 'Accept-Language': 'az,ru;q=0.9'})
    r = s.get(url, timeout=20)
    r.encoding = r.apparent_encoding or 'utf-8'
    return r

def check_lalafo():
    print("\n" + "="*60 + "\n🔍 LALAFO.AZ\n" + "="*60)
    url = 'https://lalafo.az/azerbaijan/nedvizhimost/arenda-kvartir'
    r = get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Ищем ссылки на объявления
    ad_links = [a.get('href','') for a in soup.select('a[href]')
                if re.search(r'/\d{6,}', a.get('href',''))]
    print(f"Ссылки на объявления: {ad_links[:5]}")

    # Блоки с AZN
    azn_blocks = re.findall(r'(.{0,50}\d+\s*AZN.{0,50})', r.text, re.IGNORECASE)
    print(f"Блоки с AZN (первые 3):")
    for b in azn_blocks[:3]: print(f"  {b.strip()}")

    # Блоки с otaqlı
    otaq_blocks = re.findall(r'(.{0,30}\d+\s*otaqlı.{0,30})', r.text, re.IGNORECASE)
    print(f"Блоки с otaqlı (первые 3):")
    for b in otaq_blocks[:3]: print(f"  {b.strip()}")

    # Классы содержащие "ad" или "tile" или "card"
    from collections import Counter
    cls = Counter()
    for t in soup.find_all(True):
        for c in t.get('class', []):
            if any(x in c.lower() for x in ['ad','tile','card','item','list','elan']):
                cls[c] += 1
    print(f"Классы карточек:")
    for c, n in cls.most_common(10): print(f"  .{c} × {n}")

def check_arenda():
    print("\n" + "="*60 + "\n🔍 ARENDA.AZ\n" + "="*60)
    url = 'https://arenda.az/kiraye/menzil'
    r = get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    ad_links = [a.get('href','') for a in soup.select('a[href]')
                if re.search(r'/\d{4,}', a.get('href',''))]
    print(f"Ссылки на объявления: {ad_links[:5]}")

    # Блоки с ценой
    price_blocks = re.findall(r'(.{0,40}\d+\s*(?:AZN|₼).{0,40})', r.text, re.IGNORECASE)
    print(f"Блоки с ценой:")
    for b in price_blocks[:5]: print(f"  {b.strip()}")

    # Классы
    from collections import Counter
    cls = Counter()
    for t in soup.find_all(True):
        for c in t.get('class', []):
            if any(x in c.lower() for x in ['elan','item','card','list','prop','flat']):
                cls[c] += 1
    print(f"Классы карточек:")
    for c, n in cls.most_common(10): print(f"  .{c} × {n}")

    # Первый блок с otaqlı
    otaq = re.findall(r'(.{0,80}\d+\s*otaqlı.{0,80})', r.text, re.IGNORECASE)
    print(f"Блоки otaqlı: {otaq[:3]}")

def check_bina_api():
    print("\n" + "="*60 + "\n🔍 BINA.AZ — __NEXT_DATA__\n" + "="*60)
    r = get('https://bina.az/baki/kiraye/menziller')
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            print(f"✅ __NEXT_DATA__ найден! Размер: {len(m.group(1))} символов")
            # Ключи верхнего уровня
            def show_keys(d, indent=0, depth=0):
                if depth > 3: return
                if isinstance(d, dict):
                    for k, v in list(d.items())[:8]:
                        vtype = type(v).__name__
                        vlen = len(v) if isinstance(v, (list,dict,str)) else ''
                        print(' '*indent + f"'{k}': {vtype} {vlen}")
                        if isinstance(v, dict) and depth < 2:
                            show_keys(v, indent+2, depth+1)
                        elif isinstance(v, list) and v and isinstance(v[0], dict):
                            print(' '*(indent+2) + f"[0] keys: {list(v[0].keys())[:6]}")
            show_keys(data)
        except Exception as e:
            print(f"JSON parse error: {e}")
    else:
        print("❌ __NEXT_DATA__ не найден")
        # Ищем другие JSON блоки
        jsons = re.findall(r'window\.__(\w+)\s*=\s*({.*?});\s*</script>', r.text, re.DOTALL)
        for name, j in jsons[:3]:
            print(f"  window.__{name}: {j[:100]}")

def check_tap_api():
    print("\n" + "="*60 + "\n🔍 TAP.AZ — API / __NEXT_DATA__\n" + "="*60)
    r = get('https://tap.az/elanlar/dasinmaz-emlak/menziller?p%5B740%5D=3724')
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            print(f"✅ __NEXT_DATA__ найден! {len(m.group(1))} символов")
            def show_keys(d, indent=0, depth=0):
                if depth > 3: return
                if isinstance(d, dict):
                    for k, v in list(d.items())[:8]:
                        vlen = len(v) if isinstance(v,(list,dict,str)) else ''
                        print(' '*indent + f"'{k}': {type(v).__name__} {vlen}")
                        if isinstance(v, dict) and depth < 2:
                            show_keys(v, indent+2, depth+1)
                        elif isinstance(v, list) and v and isinstance(v[0], dict):
                            print(' '*(indent+2) + f"[0] keys: {list(v[0].keys())[:6]}")
            show_keys(data)
        except Exception as e:
            print(f"JSON error: {e}")
    else:
        print("❌ __NEXT_DATA__ не найден")
        jsons = re.findall(r'window\.__(\w+)\s*=\s*({.*?});\s*(?:</script>|var )', r.text, re.DOTALL)
        for name, j in jsons[:3]: print(f"  window.__{name}: {j[:150]}")
        # API calls in JS
        api_urls = re.findall(r'["\'](https?://[^"\']*api[^"\']{5,})["\']', r.text)
        print(f"API URLs в JS: {api_urls[:5]}")

if __name__ == '__main__':
    check_lalafo()
    check_arenda()
    check_bina_api()
    check_tap_api()
    print("\n✅ Готово!")
