#!/usr/bin/env python3
"""Validate C14 raw files. python3 check_raw.py [s1|s2] [Sxx ...]"""
import sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
MAX = [4, 4, 4, 4, 3, 4, 10]


def load_raw(p, cards=None, only=None):
    mp = pd.read_csv(HERE / 'mapping.csv').set_index('code')['set'].to_dict()
    if cards is None:
        cards = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
    out, errors = {}, []
    files = sorted((HERE / 'raw' / p).glob('S*.txt'))
    if only: files = [f for f in files if f.stem in only]
    for f in files:
        s = mp[f.stem]; ids = set(cards.loc[cards['set'] == s, 'id']); seen = set()
        for n, line in enumerate(f.read_text().splitlines(), 1):
            t = line.split()
            if not t: continue
            try:
                v = [int(x) for x in t]
            except ValueError:
                errors.append(f'{p}/{f.name}:{n} non-integer: {line[:60]!r}'); continue
            if len(v) != 8: errors.append(f'{p}/{f.name}:{n} needs 8 fields'); continue
            if v[0] not in ids: errors.append(f'{p}/{f.name}:{n} unknown id {v[0]}'); continue
            if v[0] in seen: errors.append(f'{p}/{f.name}:{n} duplicate id {v[0]}'); continue
            if any(x < 0 or x > mx for x, mx in zip(v[1:], MAX)): errors.append(f'{p}/{f.name}:{n} out of range'); continue
            seen.add(v[0]); out[(s, v[0])] = v[1:]
        miss = ids - seen
        if miss: errors.append(f'{p}/{f.name}: missing {len(miss)} cards')
    return out, errors


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else 's1'
    out, errs = load_raw(p, only=sys.argv[2:] or None)
    print(f'{p}: extracted {len(out)} (7210 when complete), errors {len(errs)}')
    for e in errs[:30]: print(e)
