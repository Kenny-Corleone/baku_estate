"""Debug bina.az parser - check full structure"""
import requests
import json
import re

url = 'https://bina.az/baki/kiraye/menziller?page=1'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

s = requests.Session()
s.headers.update({'User-Agent': UA})
resp = s.get(url, timeout=20)

m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
if m:
    data = json.loads(m.group(1))
    
    # Print full structure
    print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
    
    # Look for items in different places
    def find_items(obj, path="", depth=0):
        if depth > 10:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if k in ['items', 'ads', 'listings', 'data', 'results'] and isinstance(v, list) and len(v) > 0:
                    print(f"\n✅ Found array at: {new_path} with {len(v)} items")
                    if v and isinstance(v[0], dict):
                        print(f"First item keys: {list(v[0].keys())[:10]}")
                find_items(v, new_path, depth+1)
        elif isinstance(obj, list) and len(obj) > 0:
            find_items(obj[0], f"{path}[0]", depth+1)
    
    print("\n\nSearching for items...")
    find_items(data)
