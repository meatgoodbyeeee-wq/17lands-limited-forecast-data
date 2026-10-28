"""Lists which G3 training-set passes exist (Plan A). python3 status_all.py"""
import json
from pathlib import Path
H = Path(__file__).resolve().parent; miss = []; done = 0
for k in sorted((H/'keys_all').glob('*.csv')):
    s = k.stem; n = sum(1 for _ in open(k)) - 1; p = H/'all'/s/'pass1.json'; ok = False
    if p.exists():
        try: ok = len(json.load(open(p))) == n
        except Exception: ok = False
    done += ok
    if not ok: miss.append(s)
print('done', done, 'missing', len(miss), miss)
