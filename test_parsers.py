"""
Test individual parsers to identify issues
"""
import sys
import io
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from parsers.bina import parse_bina
from parsers.tap import parse_tap
from parsers.arenda import parse_arenda
from parsers.ev10 import parse_ev10
from parsers.houses import parse_houses
from parsers.tikili import parse_tikili
from parsers.emlakbazari import parse_emlakbazari
from parsers.binalar import parse_binalar
from parsers.yeniemlak import parse_yeniemlak
from parsers.villa import parse_villa
from parsers.vipemlak import parse_vipemlak
from parsers.rahatemlak import parse_rahatemlak
from parsers.binatap import parse_binatap
from parsers.yekemlak import parse_yekemlak
from parsers.rns import parse_rns
from parsers.etagi import parse_etagi

PARSERS = {
    'bina': parse_bina,
    'tap': parse_tap,
    'arenda': parse_arenda,
    'ev10': parse_ev10,
    'houses': parse_houses,
    'tikili': parse_tikili,
    'emlakbazari': parse_emlakbazari,
    'binalar': parse_binalar,
    'yeniemlak': parse_yeniemlak,
    'villa': parse_villa,
    'vipemlak': parse_vipemlak,
    'rahatemlak': parse_rahatemlak,
    'binatap': parse_binatap,
    'yekemlak': parse_yekemlak,
    'rns': parse_rns,
    'etagi': parse_etagi,
}

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        name = sys.argv[1]
        if name in PARSERS:
            print(f"\n{'='*60}")
            print(f"Testing {name}")
            print('='*60)
            results = PARSERS[name](pages=1)
            print(f"\nResults: {len(results)} listings")
            if results:
                print("\nSample listing:")
                print(results[0])
        else:
            print(f"Unknown parser: {name}")
            print(f"Available: {', '.join(PARSERS.keys())}")
    else:
        print("Testing all parsers...")
        for name, fn in PARSERS.items():
            print(f"\n{'='*60}")
            print(f"Testing {name}")
            print('='*60)
            try:
                results = fn(pages=1)
                print(f"✅ {name}: {len(results)} listings")
                if results:
                    print(f"Sample: {results[0]['title'][:50]}")
            except Exception as e:
                print(f"❌ {name}: {e}")
