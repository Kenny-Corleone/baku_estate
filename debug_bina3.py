"""Debug bina.az API"""
import requests
import json

# Try their API endpoint
urls = [
    'https://bina.az/api/items?city_id=1&category_id=1&leased=true&page=1',
    'https://api.bina.az/items?city_id=1&category_id=1&leased=true&page=1',
    'https://bina.az/api/v1/items?city_id=1&category_id=1&leased=true&page=1',
    'https://bina.az/api/search?city_id=1&category_id=1&leased=true&page=1',
]

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

for url in urls:
    print(f"\nTrying: {url}")
    try:
        s = requests.Session()
        s.headers.update({
            'User-Agent': UA,
            'Accept': 'application/json',
            'Referer': 'https://bina.az/baki/kiraye/menziller',
        })
        resp = s.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"JSON keys: {list(data.keys())[:10]}")
                if 'items' in data:
                    print(f"✅ Found {len(data['items'])} items!")
                    if data['items']:
                        print(f"First item keys: {list(data['items'][0].keys())}")
                        break
            except:
                print(f"Not JSON, length: {len(resp.text)}")
    except Exception as e:
        print(f"Error: {e}")
