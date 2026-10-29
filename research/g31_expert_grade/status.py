import json
from pathlib import Path
H = Path(__file__).resolve().parent; miss = []
if not (H/'lessons_cu.md').exists(): miss.append('lessons_cu')
for s in ['FRA', 'TMT', 'ECL']:
    n = sum(1 for _ in open(H/'keys'/f'{s}.csv')) - 1
    for k in (1, 2):
        p = H/s/f'pass{k}.json'
        try: ok = len(json.load(open(p))) == n
        except Exception: ok = False
        if not ok: miss.append(f'{s} pass{k}')
print('missing:', miss or 'none -> run python3 score.py')
