#!/usr/bin/env python3
"""Validate C10 raw files against targets (format, ranges, coverage).

  python3 check_raw.py [r1|r2]
"""
import re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
LINE = re.compile(r'^(\d+) \| ([^|]{1,400}) \| (\d{1,3}) (\d{1,2}) ([0-3])\s*$')
PASSES = ['r1', 'r2']


def load_raw(p):
    out, errors = {}, []
    for f in sorted((HERE / 'raw' / p).glob('*.txt')):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            m = LINE.match(line.strip())
            if not m:
                errors.append(f'{p}/{f.name}:{n} bad format: {line[:120]!r}'); continue
            pct, gr = int(m.group(3)), int(m.group(4))
            if pct > 100 or pct % 5 or gr > 10:
                errors.append(f'{p}/{f.name}:{n} out of range: {line[:120]!r}'); continue
            cid = int(m.group(1))
            if cid in out:
                errors.append(f'{p}/{f.name}:{n} duplicate id {cid}')
            out[cid] = (pct, gr, int(m.group(5)))
    return out, errors


if __name__ == '__main__':
    t = pd.read_csv(HERE / 'targets.csv')
    need = set(t.loc[t['target'] == 1, 'id'])
    bad = False
    for p in (sys.argv[1:] or PASSES):
        raw, errors = load_raw(p)
        miss, extra = sorted(need - set(raw)), sorted(set(raw) - need)
        print(f'{p}: targets {len(need)}, extracted {len(raw)}, missing {len(miss)}, extra {len(extra)}, format errors {len(errors)}')
        for e in errors[:10]:
            print(e)
        bad |= bool(errors or extra)
    sys.exit(1 if bad else 0)
