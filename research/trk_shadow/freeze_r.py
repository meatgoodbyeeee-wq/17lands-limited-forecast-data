#!/usr/bin/env python3
"""TRK shadow arm R (PLAN_R.md): G corrected by the prior actual of reprinted cards. python3 freeze_r.py
Reads trk_frozen.csv (G), the 28-set pool actuals and research/q_small_gains/q3_cards.csv.gz (the 138 reprint rows, for k). No TRK outcomes."""
import hashlib, json, sys
from pathlib import Path
import pandas as pd
H = Path(__file__).resolve().parent; R = H.parents[0]
ORD = 'KHM STX AFR MID VOW NEO SNC DMU BRO ONE MOM LTR WOE LCI MKM OTJ BLB DSK FDN DFT TDM EOE TLA ECL TMT SOS MSH HOB'.split()
sys.path.insert(0, str(R / 'c9_power_questions')); sys.path.insert(0, str(R / 'c5_atomic_effects'))
_a, sys.argv = sys.argv, ['c9']
import c9  # noqa: E402
sys.argv = _a
pool = c9.load_pool()[0][['set', 'name', 'type_line', 'actual_gih']].copy()
assert sorted(pool['set'].unique()) == sorted(ORD)
pool['delta'] = (pool.actual_gih - pool.groupby('set').actual_gih.transform('mean')) * 100
pool['i'] = pool['set'].map({s: i for i, s in enumerate(ORD)})
pool = pool[~pool.type_line.str.contains('Basic Land')]
q = pd.read_csv(R / 'q_small_gains/q3_cards.csv.gz'); assert len(q) == 138
k = float((q.d * q.resid).sum() / (q.d ** 2).sum())
f = pd.read_csv(H / 'trk_frozen.csv'); m = f.G.mean(); rows = []
for r in f.itertuples():
    p = pool[pool.name == r.name]
    if len(p) and 'Basic Land' not in str(r.name):
        last = p[p.i == p.i.max()]; d = float(last.delta.mean()) - (r.G - m)
        rows.append({'id': r.id, 'name': r.name, 'rarity': r.rarity, 'G': r.G, 'R': round(r.G + k * d, 4), 'prior_set': ORD[int(p.i.max())], 'prior_delta': round(float(last.delta.mean()), 3)})
    else:
        rows.append({'id': r.id, 'name': r.name, 'rarity': r.rarity, 'G': r.G, 'R': r.G, 'prior_set': '', 'prior_delta': ''})
out = pd.DataFrame(rows); out.to_csv(H / 'trk_frozen_R.csv', index=False)
n = int((out.prior_set != '').sum())
meta = {'k': k, 'reprint_cards': n, 'trk_frozen_R_csv_sha256': hashlib.sha256((H / 'trk_frozen_R.csv').read_bytes()).hexdigest(),
        'trk_frozen_csv_sha256': hashlib.sha256((H / 'trk_frozen.csv').read_bytes()).hexdigest()}
(H / 'frozen_R.json').write_text(json.dumps(meta, indent=1) + '\n'); print(meta)
x = out[out.prior_set != ''].copy(); x['change'] = x.R - x.G
print(x[['name', 'rarity', 'prior_set', 'prior_delta', 'G', 'R', 'change']].round(2).to_string(index=False))
