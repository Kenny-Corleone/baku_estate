"""
Fix all parsers by checking actual HTML structure
"""
import requests
from bs4 import BeautifulSoup
import re

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

sites = {
    'bina': 'https://bina.az/baki/kiraye/menziller',
    'tap': 'https://tap.az/elanlar/dasinmaz-emlak/menziller',
    'arenda': 'https://arenda.az/kiraye/menzil',
    'ev10': 'https://ev10.az/elanlar/dasinmaz-emlak/menziller',
    'houses': 'https://houses.az/elanlar',
    'tikili': 'https://tikili.az/elanlar',
    'emlakbazari': 'https://emlakbazari.az/elanlar',
    'binalar': 'https://binalar.az/menziller',
    'yeniemlak': 'https://yeniemlak.az',
    'villa': 'https://villa.az/elanlar',
    'vipemlak': 'https://vipemlak.az',
    'rahatemlak': 'https://rahatemlak.az',
    'binatap': 'https://binatap.az',
    'yekemlak': 'https://yekemlak.az',
    'etagi': 'https://baku.etagi.com/realty',
}

for name, url in sites.items():
    print(f"\n{'='*60}")
    print(f"{name}: {url}")
    print('='*60)
    
    try:
        s = requests.Session()
        s.headers['User-Agent'] = UA
        resp = s.get(url, timeout=15)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code != 200:
            continue
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find potential listing containers
        selectors = [
            'article', '.item', '.card', '.listing', '.ad', '.property',
            '[class*="item"]', '[class*="card"]', '[class*="listing"]',
            '[class*="product"]', '[class*="ad-"]', '[data-item-id]'
        ]
        
        for sel in selectors:
            cards = soup.select(sel)
            if len(cards) >= 5:
                print(f"✅ Found {len(cards)} elements with selector: {sel}")
                
                # Check first card
                card = cards[0]
                link = card.select_one('a[href]')
                if link:
                    print(f"   Link: {link.get('href', '')[:60]}")
                
                price = card.select_one('[class*="price"]')
                if price:
                    print(f"   Price text: {price.get_text()[:40]}")
                
                title = card.select_one('h2, h3, [class*="title"]')
                if title:
                    print(f"   Title: {title.get_text()[:50]}")
                
                break
        else:
            print("❌ No listing cards found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
