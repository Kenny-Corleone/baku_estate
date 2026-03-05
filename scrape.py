"""
EvTap — Scrape Pipeline (Paralel)
20 parseri paralel işə salır → data/listings.json
"""

import json
import time
import os
import sys
import io
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def _is_probably_listing(item: dict) -> bool:
    if not item or not isinstance(item, dict):
        return False
    if not item.get('id'):
        return False
    link = str(item.get('link') or '')
    if not link.startswith('http'):
        return False
    title = str(item.get('title') or '')
    district = str(item.get('district') or '')
    text = (title + ' ' + district).lower()
    bad_words = [
        'статья', 'новости', 'xəbər', 'xəbərlər', 'blog', 'read more',
        'fact-checked', 'trusted authors', 'terms', 'qaydalar',
        'лучшие предложения',
    ]
    if any(w in text for w in bad_words):
        return False

    if len(title) > 140 or len(district) > 140:
        return False

    source = str(item.get('source') or '')
    has_signal = bool(item.get('price')) or bool(item.get('rooms')) or bool(item.get('area'))
    if not has_signal:
        # Some sources may omit these fields; allow if link pattern looks like a listing.
        if source in {'emlak_gov'}:
            return True
        if any(p in link for p in ['/items/', '/posting/', '/property/', '/elan/', 'elan-item.php?elan=']):
            return True
        return False

    return True

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s — %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

from parsers.bina import parse_bina
from parsers.tap import parse_tap
from parsers.lalafo import parse_lalafo
from parsers.arenda import parse_arenda
from parsers.emlak import parse_emlak
from parsers.ev10 import parse_ev10
from parsers.houses import parse_houses
from parsers.emlakbazari import parse_emlakbazari
from parsers.tikili import parse_tikili
from parsers.kub import parse_kub
from parsers.yeniemlak import parse_yeniemlak
from parsers.binalar import parse_binalar
from parsers.villa import parse_villa
from parsers.vipemlak import parse_vipemlak
from parsers.rahatemlak import parse_rahatemlak
from parsers.binatap import parse_binatap
from parsers.yekemlak import parse_yekemlak
from parsers.rns import parse_rns
from parsers.etagi import parse_etagi
from parsers.emlak_gov import parse_emlak_gov

PARSERS = {
    'bina': parse_bina, 'tap': parse_tap, 'lalafo': parse_lalafo,
    'arenda': parse_arenda, 'emlak': parse_emlak, 'ev10': parse_ev10,
    'houses': parse_houses, 'emlakbazari': parse_emlakbazari,
    'tikili': parse_tikili, 'kub': parse_kub, 'yeniemlak': parse_yeniemlak,
    'binalar': parse_binalar, 'villa': parse_villa, 'vipemlak': parse_vipemlak,
    'rahatemlak': parse_rahatemlak, 'binatap': parse_binatap,
    'yekemlak': parse_yekemlak, 'rns': parse_rns, 'etagi': parse_etagi,
    'emlak_gov': parse_emlak_gov,
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'listings.json')


def _run_parser(name, fn, pages=1):
    """Bir parseri işə sal, nəticədə (ad, elanlar) qaytar."""
    try:
        log.info(f"  {name} parserlənir...")
        results = fn(pages=pages)
        valid = [r for r in results if _is_probably_listing(r)]
        seen = set()
        unique = []
        for item in valid:
            if item['id'] not in seen:
                seen.add(item['id'])
                item['timestamp'] = time.time()
                unique.append(item)
        log.info(f"  OK {name}: {len(unique)} elan")
        return name, unique
    except Exception as e:
        log.error(f"  ERROR {name} xətası: {e}")
        return name, []


def run_all_parsers():
    log.info("20 mənbənin paralel parserlənməsi başlanır...")
    start = time.time()
    all_listings = []
    source_stats = {}

    # 5 ayni anda parserlə (serverləri yükləməmək üçün)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_run_parser, name, fn, 1): name
            for name, fn in PARSERS.items()
        }
        for future in as_completed(futures):
            name, items = future.result()
            source_stats[name] = len(items)
            all_listings.extend(items)

    elapsed = round(time.time() - start, 1)

    prices = [l['price'] for l in all_listings if l.get('price')]
    avg_price = round(sum(prices) / len(prices)) if prices else 0

    by_rooms, by_property_type, by_deal_type = {}, {}, {}
    for l in all_listings:
        r = str(l.get('rooms', '?'))
        by_rooms[r] = by_rooms.get(r, 0) + 1
        pt = l.get('property_type', 'menzil')
        by_property_type[pt] = by_property_type.get(pt, 0) + 1
        dt = l.get('deal_type', 'kiraye')
        by_deal_type[dt] = by_deal_type.get(dt, 0) + 1

    output = {
        'listings': all_listings,
        'stats': {
            'total': len(all_listings),
            'avg_price': avg_price,
            'by_source': source_stats,
            'by_rooms': by_rooms,
            'by_property_type': by_property_type,
            'by_deal_type': by_deal_type,
        },
        'scan_time': datetime.now(timezone.utc).isoformat(),
        'scan_timestamp': time.time(),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"Tamamlandı {elapsed} san-da. Cəmi: {len(all_listings)} elan")
    log.info(f"Mənbələr: {source_stats}")
    return output


if __name__ == '__main__':
    run_all_parsers()
