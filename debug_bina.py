"""Debug bina.az parser"""
import sys
import io
import requests
import json
import re

if sys.stdout and getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and getattr(sys.stderr, "encoding", None) and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

url = 'https://bina.az/baki/kiraye/menziller?page=1'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

s = requests.Session()
s.headers.update({'User-Agent': UA})
resp = s.get(url, timeout=20)

print(f"Status: {resp.status_code}")
print(f"Content length: {len(resp.text)}")

# Check for __NEXT_DATA__
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
if m:
    print("\nFound __NEXT_DATA__")
    data = json.loads(m.group(1))
    
    # Check apolloState
    apollo = data.get('props', {}).get('initialState', {}).get('apolloState', {})
    if not apollo:
        apollo = data.get('apolloState', {})
    
    print(f"Apollo keys: {len(apollo)}")
    
    # Find Item: keys
    items = [k for k in apollo.keys() if k.startswith('Item:')]
    print(f"Item: keys found: {len(items)}")
    
    if items:
        print(f"\nSample item key: {items[0]}")
        print(json.dumps(apollo[items[0]], indent=2, ensure_ascii=False)[:500])
    
    # Check pageProps
    page_props = data.get('props', {}).get('initialProps', {}).get('pageProps', {})
    if page_props:
        print(f"\npageProps keys: {list(page_props.keys())}")
        for key in ['items', 'listings', 'data', 'ads']:
            if key in page_props:
                print(f"  {key}: {len(page_props[key])} items")
else:
    print("\n❌ __NEXT_DATA__ not found")
    print("\nFirst 1000 chars:")
    print(resp.text[:1000])
