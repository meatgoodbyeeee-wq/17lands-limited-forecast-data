"""Lists which G3 outputs exist and which are missing (for resuming)."""
import json
from pathlib import Path
H = Path(__file__).resolve().parent; miss = []
print('lessons.md', 'OK' if (H/'lessons.md').exists() else 'MISSING')
if not (H/'lessons.md').exists(): miss.append('lessons')
for s in ['FRA', 'TMT', 'ECL']:
    n = sum(1 for _ in open(H/s/'targets_key.csv')) - 1
    for k in (1, 2, 3):
        p = H/s/f'pass{k}.json'; ok = False
        if p.exists():
            try: ok = len(json.load(open(p))) == n
            except Exception: ok = False
        print(s, f'pass{k}', 'OK' if ok else 'MISSING/INVALID')
        if not ok: miss.append(f'{s} pass{k}')
print('missing:', miss or 'none -> run python3 score.py')
