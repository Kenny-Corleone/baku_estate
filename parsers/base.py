"""
EvTap — Baza parser utilitləri
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
]

# ── Əmlak tipləri ────────────────────────────────────────────────────────────
PROPERTY_TYPES = {
    'menzil': 'Mənzil',
    'ev_villa': 'Ev / Villa',
    'ofis': 'Ofis',
    'torpaq': 'Torpaq',
    'kommersiya': 'Kommersiya',
    'qaraj': 'Qaraj',
    'diger': 'Digər',
}

DEAL_TYPES = {
    'kiraye': 'Kirayə',
    'satis': 'Satış',
}

DISTRICTS_BAKU = [
    'Binəqədi', 'Xətai', 'Xəzər', 'Nərimanov', 'Nəsimi', 'Nizami',
    'Pirallahı', 'Qaradağ', 'Sabail', 'Sabunçu', 'Səbail', 'Suraxanı',
    'Yasamal', 'Badamdar', 'Bayıl', 'Həzi Aslanov', 'İnşaatçılar',
    'Əhmədli', 'Bakıxanov', 'Biləcəri', 'Buzovna', 'Digah', 'Hövsan',
    'Maştağa', 'Mərdəkan', 'Novxanı', 'Pirşağı', 'Ramana', 'Şüvəlan',
    'Türkan', 'Yeni Günəşli', 'Köhnə Günəşli', 'Zabrat',
    '20 Yanvar', '28 May', 'Elmlər Akademiyası', 'Gənclik', 'Xalqlar',
    'İçərişəhər', 'Koroğlu', 'Memar Əcəmi', 'Neftçilər', 'Sahil',
    'Ulduz', 'Azadlıq',
]


def make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'az-AZ,az;q=0.9,ru;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return s


def fetch(url: str, timeout: int = 20, retries: int = 3):
    for attempt in range(retries):
        try:
            session = make_session()
            time.sleep(random.uniform(0.3, 0.8))
            resp = session.get(url, timeout=timeout)
            print(f"    [{resp.status_code}] {url}")

            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or 'utf-8'
                text = resp.text
                if '<html' in text.lower() or '<div' in text.lower() or 'otaq' in text.lower():
                    return BeautifulSoup(text, 'html.parser')
                else:
                    print(f"    ⚠️  Cavab HTML deyil (ilk 100 bayt): {repr(text[:100])}")
                    return None

            elif resp.status_code in (301, 302):
                new_url = resp.headers.get('Location', '')
                print(f"    ↩️  Yönləndirmə: {new_url}")
                if new_url:
                    url = new_url
                    continue

            elif resp.status_code == 403:
                print(f"    ❌ 403 Bloklanıb — cəhd {attempt+1}/{retries}")
                time.sleep(5 * (attempt + 1))

            else:
                print(f"    ❌ HTTP {resp.status_code}")
                return None
        except Exception as e:
            print(f"    ❌ Xəta: {e}")
            time.sleep(3)
    return None


def fetch_rendered(
    url: str,
    timeout: int = 30,
    wait_until: str = 'networkidle',
    wait_for_selector: str | None = None,
):
    """Fetch HTML using a headless browser (Playwright) for JS-rendered pages."""
    if sync_playwright is None:
        raise RuntimeError('Playwright is not installed. Install it and run: playwright install')

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
            ],
        )
        try:
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale='az-AZ',
                extra_http_headers={
                    'Accept-Language': 'az-AZ,az;q=0.9,ru;q=0.8,en;q=0.7',
                },
            )
            page = context.new_page()
            page.set_default_timeout(timeout * 1000)
            page.goto(url, wait_until=wait_until)
            if wait_for_selector:
                page.wait_for_selector(wait_for_selector)
            html = page.content()
            return BeautifulSoup(html, 'html.parser')
        finally:
            browser.close()


def fetch_json(url: str, timeout: int = 15, headers: dict = None):
    """JSON API sorğusu üçün"""
    try:
        session = make_session()
        if headers:
            session.headers.update(headers)
        session.headers['Accept'] = 'application/json, text/plain, */*'
        time.sleep(random.uniform(0.5, 1.5))
        resp = session.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    ❌ JSON xəta: {e}")
    return None


def make_id(source, raw_id):
    return f"{source}_{raw_id}"


def clean_price(text):
    if not text:
        return None
    digits = re.sub(r'[^\d]', '', str(text))
    return int(digits) if digits else None


def clean_text(text):
    return ' '.join(str(text).split()).strip() if text else ''


def extract_rooms(text):
    if not text:
        return None
    m = re.search(r'(\d+)\s*[-\s]?otaq', str(text), re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*комн', str(text), re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*[-\s]?room', str(text), re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def extract_area(text):
    if not text:
        return None
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', str(text), re.IGNORECASE)
    if m:
        return float(m.group(1).replace(',', '.'))
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*kv\.?\s*m', str(text), re.IGNORECASE)
    if m:
        return float(m.group(1).replace(',', '.'))
    return None


def extract_floor(text):
    if not text:
        return None, None
    m = re.search(r'(\d+)\s*/\s*(\d+)', str(text))
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def detect_property_type(text):
    """Mətndən əmlak tipini müəyyən et"""
    if not text:
        return 'menzil'
    t = str(text).lower()
    if any(w in t for w in ['villa', 'həyət', 'bağ evi', 'ev ', 'house', 'cottage']):
        return 'ev_villa'
    if any(w in t for w in ['ofis', 'office']):
        return 'ofis'
    if any(w in t for w in ['torpaq', 'land']):
        return 'torpaq'
    if any(w in t for w in ['mağaza', 'dükan', 'anbar', 'kommersiya', 'commercial', 'obyekt']):
        return 'kommersiya'
    if any(w in t for w in ['qaraj', 'garage']):
        return 'qaraj'
    return 'menzil'


def detect_deal_type(text, url=''):
    """Mətndən/URL-dən sövdələşmə tipini müəyyən et"""
    combined = (str(text) + ' ' + str(url)).lower()
    if any(w in combined for w in ['satış', 'satılır', 'satıl', 'sale', 'sell', 'alqi-satqi', 'satis']):
        return 'satis'
    return 'kiraye'


def detect_district(text):
    """Mətndən rayonu müəyyən et"""
    if not text:
        return 'Bakı'
    for d in DISTRICTS_BAKU:
        if d.lower() in str(text).lower():
            return d
    return clean_text(text)[:50] or 'Bakı'


def make_listing(source, source_name, raw_id, **kwargs):
    """Standart elan obyekti yarat"""
    return {
        'id': make_id(source, raw_id),
        'source': source,
        'source_name': source_name,
        'link': kwargs.get('link', ''),
        'price': kwargs.get('price'),
        'title': str(kwargs.get('title', 'Elan'))[:80],
        'district': str(kwargs.get('district', 'Bakı'))[:50],
        'rooms': kwargs.get('rooms'),
        'area': kwargs.get('area'),
        'floor': kwargs.get('floor'),
        'total_floors': kwargs.get('total_floors'),
        'photo': kwargs.get('photo', ''),
        'property_type': kwargs.get('property_type', 'menzil'),
        'deal_type': kwargs.get('deal_type', 'kiraye'),
        'contact_name': kwargs.get('contact_name', ''),
        'contact_phone': kwargs.get('contact_phone', ''),
        'is_new': True,
    }
