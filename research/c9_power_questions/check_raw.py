#!/usr/bin/env python3
"""Build pass-specific inputs and validate C9 raw files (format, ranges, coverage).

  python3 check_raw.py inputs        # writes input/p{1,2,3}/bXX.txt (same cards, different order per pass)
  python3 check_raw.py [p1|p2|p3]    # validate one pass (default: all)
"""
import random, re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[0] / 'c5_atomic_effects' / 'input'
FIELDS = ['IMP', 'UNA', 'VAL', 'FLOOR', 'FLEX', 'PLAY', 'GRADE']
MAX = [4, 4, 4, 4, 3, 4, 10]
LINE = re.compile(r'^(\d+)((?: \d+){7})\s*$')
PASSES = ['p1', 'p2', 'p3']


def make_inputs():
    for p in PASSES:
        (HERE / 'input' / p).mkdir(parents=True, exist_ok=True)
    for f in sorted(SRC.glob('b*.txt')):
        txt = f.read_text()
        cards = [c.strip() for c in re.split(r'\n(?=#\d+ \|)', txt.split('\n-- batch')[0]) if c.strip().startswith('#')]
        for i, p in enumerate(PASSES):
            order = list(cards)
            if p == 'p2':
                order = order[::-1]
            elif p == 'p3':
                random.Random(int(f.stem[1:]) * 7 + 3).shuffle(order)
            (HERE / 'input' / p / f.name).write_text('\n\n'.join(order) + f'\n-- {f.stem}, pass {p}: {len(order)} cards\n')


def load_raw(p):
    out, errors = {}, []
    for f in sorted((HERE / 'raw' / p).glob('b*.txt')):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            m = LINE.match(line.strip())
            if not m:
                errors.append(f'{p}/{f.name}:{n} bad format: {line!r}'); continue
            v = [int(x) for x in m.group(2).split()]
            if any(x < 0 or x > mx for x, mx in zip(v, MAX)):
                errors.append(f'{p}/{f.name}:{n} out of range: {line!r}'); continue
            cid = int(m.group(1))
            if cid in out:
                errors.append(f'{p}/{f.name}:{n} duplicate id {cid}')
            out[cid] = v
    return out, errors


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'inputs':
        make_inputs(); print('inputs written'); sys.exit(0)
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    need = set(u.loc[u['auto'] == 0, 'id'])
    bad = False
    for p in ([sys.argv[1]] if len(sys.argv) > 1 else PASSES):
        raw, errors = load_raw(p)
        miss, extra = sorted(need - set(raw)), sorted(set(raw) - need)
        print(f'{p}: cards {len(need)}, extracted {len(raw)}, missing {len(miss)}, extra {len(extra)}, format errors {len(errors)}')
        for e in errors[:10]:
            print('  ', e)
        bad |= bool(errors or miss or extra)
    sys.exit(1 if bad else 0)
