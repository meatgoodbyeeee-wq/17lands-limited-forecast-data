#!/usr/bin/env python3
"""Validate C12 raw files. python3 check_raw.py [s1|s2]"""
import re, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
LINE = re.compile(r'^(\d+) \| (\d{1,2}) \| (\d{1,2}(?:\.\d)?) \| (\d{1,2}(?:\.\d)?)$')


def load_raw(p, cards=None):
    mp = pd.read_csv(HERE / 'mapping.csv').set_index('code')['set'].to_dict()
    if cards is None:
        cards = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
    out, errors = {}, []
    for f in sorted((HERE / 'raw' / p).glob('S*.txt')):
        s = mp[f.stem]; g = cards[(cards['set'] == s) & (cards['target'] == 1)]; tg = list(g['id'])
        seen = []
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            m = LINE.match(line.strip())
            if not m:
                errors.append(f'{p}/{f.name}:{n} bad format: {line[:80]!r}'); continue
            i, k, on, off = int(m.group(1)), int(m.group(2)), float(m.group(3)), float(m.group(4))
            if i not in tg: errors.append(f'{p}/{f.name}:{n} id {i} not a target'); continue
            if k > 12 or on > 10 or off > 10: errors.append(f'{p}/{f.name}:{n} out of range'); continue
            if i in seen: errors.append(f'{p}/{f.name}:{n} duplicate {i}'); continue
            seen.append(i); out[(s, i)] = (k, on, off)
        miss = set(tg) - set(seen)
        if miss: errors.append(f'{p}/{f.name}: missing {len(miss)} targets')
    return out, errors


if __name__ == '__main__':
    for p in (sys.argv[1:] or ['s1', 's2']):
        out, errs = load_raw(p)
        print(f'{p}: extracted {len(out)} (expected 1067 when complete), errors {len(errs)}')
        for e in errs[:30]: print(e)
