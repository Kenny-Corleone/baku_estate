"""
EvTap — Lokal inkişaf serveri
20 parser + statik frontend
"""

from flask import Flask, jsonify, send_from_directory, request as freq, Response
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
import threading
import time
import json
import os
import sys
import io
import logging
import requests as req
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout and getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and getattr(sys.stderr, "encoding", None) and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s — %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')


def _is_probably_listing(item: dict) -> bool:
    if not item or not isinstance(item, dict):
        return False
    if not item.get('id'):
        return False
    source = str(item.get('source') or '')
    if source in {'houses', 'yekemlak'}:
        return False
    link = str(item.get('link') or '')
    if not link.startswith('http'):
        return False
    if '/agent/' in link:
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

    has_any = bool(title.strip()) or bool(district.strip()) or bool(item.get('price')) or bool(item.get('rooms')) or bool(item.get('area'))
    if not has_any:
        return False

    if source == 'rns' and '/property/' not in link:
        return False

    return True

# ─── Yaddaşda saxlama ────────────────────────────────────────────────────────
listings_db = {}
seen_ids = set()
lock = threading.Lock()

PARSERS = {
    'bina': parse_bina,
    'tap': parse_tap,
    'lalafo': parse_lalafo,
    'arenda': parse_arenda,
    'emlak': parse_emlak,
    'ev10': parse_ev10,
    'houses': parse_houses,
    'emlakbazari': parse_emlakbazari,
    'tikili': parse_tikili,
    'kub': parse_kub,
    'yeniemlak': parse_yeniemlak,
    'binalar': parse_binalar,
    'villa': parse_villa,
    'vipemlak': parse_vipemlak,
    'rahatemlak': parse_rahatemlak,
    'binatap': parse_binatap,
    'yekemlak': parse_yekemlak,
    'rns': parse_rns,
    'etagi': parse_etagi,
    'emlak_gov': parse_emlak_gov,
}

REFRESH_INTERVAL = 270  # 4.5 dəqiqə


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory('data', filename)


@app.route('/api/listings')
def get_listings():
    with lock:
        items = sorted(listings_db.values(), key=lambda x: x.get('timestamp', 0), reverse=True)
    return jsonify({'listings': items, 'total': len(items)})


@app.route('/api/listings/new')
def get_new_listings():
    cutoff = time.time() - 600
    with lock:
        new = [v for v in listings_db.values() if v.get('timestamp', 0) > cutoff]
        new.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return jsonify({'listings': new, 'count': len(new)})


@app.route('/api/stats')
def get_stats():
    with lock:
        items = list(listings_db.values())
    if not items:
        return jsonify({'total': 0, 'avg_price': 0, 'by_source': {}, 'by_rooms': {}, 'by_property_type': {}, 'by_deal_type': {}})

    prices = [i['price'] for i in items if i.get('price')]
    avg = round(sum(prices) / len(prices)) if prices else 0

    by_source, by_rooms, by_property_type, by_deal_type = {}, {}, {}, {}
    for item in items:
        s = item.get('source', '?')
        by_source[s] = by_source.get(s, 0) + 1
        r = str(item.get('rooms', '?'))
        by_rooms[r] = by_rooms.get(r, 0) + 1
        pt = item.get('property_type', 'menzil')
        by_property_type[pt] = by_property_type.get(pt, 0) + 1
        dt = item.get('deal_type', 'kiraye')
        by_deal_type[dt] = by_deal_type.get(dt, 0) + 1

    return jsonify({
        'total': len(items), 'avg_price': avg,
        'by_source': by_source, 'by_rooms': by_rooms,
        'by_property_type': by_property_type, 'by_deal_type': by_deal_type,
        'last_updated': time.strftime('%H:%M:%S'),
    })


@app.route("/api/proxy-image")
def proxy_image():
    url = freq.args.get("url", "")
    if not url or not url.startswith("http"):
        return "", 400
    try:
        r = req.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        return Response(r.content, content_type=r.headers.get("content-type", "image/jpeg"))
    except:
        return "", 404


@app.route('/api/refresh', methods=['POST'])
def manual_refresh():
    threading.Thread(target=run_all_parsers, daemon=True).start()
    return jsonify({'status': 'started'})


def run_all_parsers():
    log.info("20 mənbənin parserlənməsi başlanır...")
    with lock:
        prev_seen = set(seen_ids)

    new_db = {}
    new_seen = set()
    source_new_counts = {}

    def _run_one(source_name, parse_fn):
        try:
            log.info(f"  {source_name} parserlənir...")
            return source_name, parse_fn(), None
        except Exception as e:
            return source_name, [], e

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_run_one, name, fn): name for name, fn in PARSERS.items()}
        for fut in as_completed(futures):
            source_name, results, err = fut.result()
            if err:
                log.error(f"  ERROR {source_name} xətası: {err}")
                source_new_counts[source_name] = 0
                continue

            new_count = 0
            for item in results or []:
                if not _is_probably_listing(item):
                    continue
                uid = item.get('id')
                if not uid:
                    continue
                if uid in new_seen:
                    continue
                new_seen.add(uid)
                item['timestamp'] = time.time()
                item['is_new'] = uid not in prev_seen
                new_db[uid] = item
                if uid not in prev_seen:
                    new_count += 1

            source_new_counts[source_name] = new_count
            log.info(f"  OK {source_name}: +{new_count} yeni")

    with lock:
        listings_db.clear()
        listings_db.update(new_db)
        seen_ids.clear()
        seen_ids.update(new_seen)

    total_new = sum(source_new_counts.values())
    log.info(f"Tamamlandı. Cəmi yeni: {total_new}, bazada: {len(new_db)}")

    try:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        with lock:
            items_list = list(listings_db.values())
        output = {
            'listings': items_list,
            'stats': {'total': len(items_list), 'by_source': {}},
            'scan_time': time.strftime('%Y-%m-%dT%H:%M:%S+04:00'),
            'scan_timestamp': time.time(),
        }
        with open(os.path.join(data_dir, 'listings.json'), 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"JSON yazma xətası: {e}")


def background_loop():
    while True:
        run_all_parsers()
        log.info(f"Növbəti yeniləmə {REFRESH_INTERVAL // 60} dəq. sonra.")
        time.sleep(REFRESH_INTERVAL)


if __name__ == '__main__':
    log.info("EvTap serveri başladılır... (20 mənbə)")
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    log.info("Server əlçatandır: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
