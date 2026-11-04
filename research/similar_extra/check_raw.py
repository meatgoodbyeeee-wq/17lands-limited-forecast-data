#!/usr/bin/env python3
"""Validate label/raw/cNN_{c3,c4,c5}.txt against label/cards.csv (format, ranges, coverage). Same parsers as the TRK labelling (sonnet_check.parse)."""
import sys, glob
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / 'trk_preview'))
import sonnet_check as sc  # noqa
q = pd.read_csv(HERE / 'label/cards.csv', keep_default_na=False)
need = set(q.loc[q.auto == 0, 'id']); ok = True
for p in ('c3', 'c4', 'c5'):
    d, bad = {}, []
    for f in sorted(glob.glob(str(HERE / f'label/raw/c*_{p}.txt'))):
        for n, l in enumerate(open(f).read().splitlines(), 1):
            if not l.strip(): continue
            r = sc.parse(p, l)
            if r is None or r[0] in d: bad.append(f'{f}:{n} {l!r}'); continue
            d[r[0]] = r[1]
    print(p, 'labelled', len(d), 'missing', len(need - set(d)), 'extra', len(set(d) - need), 'errors', bad[:5])
    ok &= not (bad or need - set(d) or set(d) - need)
sys.exit(0 if ok else 1)
