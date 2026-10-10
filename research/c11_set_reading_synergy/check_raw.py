#!/usr/bin/env python3
"""Validate C11 raw files against the set lists (format, ranges, ids exist, coverage).

  python3 check_raw.py [s1|s2]
"""
import re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
PASSES = ['s1', 's2']
LINE = re.compile(r'^(\d+) \| (\d{1,2}) \| (\d{1,2}(?:\.\d)?) \| D: (.*?) \| I: (.*)$')
ENTRY = re.compile(r'^(?:#(\d+)|T:([A-Za-z\-\']+))$')


def parse_list(s):
    s = s.strip()
    if s == '-' or not s:
        return [], None
    out = []
    for tok in s.split():
        m = ENTRY.match(tok)
        if not m:
            return None, f'bad entry {tok!r}'
        out.append(('id', int(m.group(1))) if m.group(1) else ('type', m.group(2)))
    if len(out) > 40:
        return None, 'more than 40 entries'
    return out, None


def load_raw(p, cards=None):
    mp = pd.read_csv(HERE / 'mapping.csv').set_index('code')['set'].to_dict()
    out, errors = {}, []
    if cards is None:
        cards = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
    for f in sorted((HERE / 'raw' / p).glob('S*.txt')):
        s = mp[f.stem]; g = cards[cards['set'] == s]; ids = set(g['id']); tg = set(g.loc[g['target'] == 1, 'id'])
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            m = LINE.match(line.strip())
            if not m:
                errors.append(f'{p}/{f.name}:{n} bad format: {line[:100]!r}'); continue
            cid, pay, exp = int(m.group(1)), int(m.group(2)), float(m.group(3))
            D, e1 = parse_list(m.group(4)); I, e2 = parse_list(m.group(5))
            if e1 or e2 or pay > 10 or exp > 15:
                errors.append(f'{p}/{f.name}:{n} {e1 or e2 or "range"}: {line[:100]!r}'); continue
            bad = [x for L in (D, I) for t, x in L if t == 'id' and x not in ids]
            if cid not in tg or bad:
                errors.append(f'{p}/{f.name}:{n} unknown target or enabler ids {bad[:3]}: {line[:80]!r}'); continue
            if (s, cid) in out:
                errors.append(f'{p}/{f.name}:{n} duplicate id {cid}')
            out[(s, cid)] = (pay, exp, D, I)
    return out, errors


if __name__ == '__main__':
    cards = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
    need = {(r.set, r.id) for r in cards[cards['target'] == 1].itertuples()}
    bad = False
    for p in (sys.argv[1:] or PASSES):
        raw, errors = load_raw(p, cards)
        miss, extra = sorted(need - set(raw)), sorted(set(raw) - need)
        print(f'{p}: targets {len(need)}, extracted {len(raw)}, missing {len(miss)}, extra {len(extra)}, format errors {len(errors)}')
        for e in errors[:10]:
            print(e)
        bad |= bool(errors or extra)
    sys.exit(1 if bad else 0)
