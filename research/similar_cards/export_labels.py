#!/usr/bin/env python3
"""Label vectors for the "similar cards" re-ranking (see PLAN.md, eval2_results.csv).

  python3 export_labels.py --fra <pages>/data/target.json.gz --trk <pages>/data/trk/target.json.gz \
      --refs <pages>/data/similar-references.json.gz --out <pages>/data/similar-labels.json.gz

Vector = AI-label columns (C3 effects, C4 fine effects, C5 atomic tags and scales, C9 power-question means) standardised with the 28-set pool's
mean/std, missing -> 0, L2-normalised and stored as integers (x1000). No outcome (GIH/ALSA) enters a vector.
"""
import argparse, gzip, json, sys, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; R = HERE.parents[0]
for p in ('c9_power_questions', 'gih_llm_extract', 'trk_preview'):
    sys.path.insert(0, str(R / p))
import c9, c3_research as c3, trk_label as t  # noqa
c5, e = c9.c5, c9.e

ap = argparse.ArgumentParser()
for k in ('fra', 'trk', 'refs', 'out'):
    ap.add_argument('--' + k, type=Path, required=True)
a = ap.parse_args()
pool, base, cols = c9.load_pool()
pool = pool.reset_index(drop=True)
lab = [c for c in pool.columns if c.startswith(('c4_', 'c5_')) and pool[c].dtype != object] + [c for c in pool.columns if c.startswith('c9_m_')] + [c for c in cols if c in pool.columns]
lab = list(dict.fromkeys(lab))
mu, sd = pool[lab].fillna(0).to_numpy(float).mean(0), pool[lab].fillna(0).to_numpy(float).std(0) + 1e-9
def vec(df):
    x = (df[lab].fillna(0).to_numpy(float) - mu) / sd
    x /= np.linalg.norm(x, axis=1, keepdims=True) + 1e-9
    return np.rint(x * 1000).astype(int).tolist()

# references: the 22-set candidate list, labels from the pool by set|name
refs = json.loads(gzip.open(a.refs, 'rt', encoding='utf-8').read())['cards']
pk = {(s, n): i for i, (s, n) in enumerate(zip(pool.set, pool.name))}
V = vec(pool)
ref_out = {f"{r['set']}|{r['name']}": V[pk[(r['set'], r['name'])]] for r in refs if (r['set'], r['name']) in pk}

# FRA: same frame as freeze_fra.py (features by key)
fra, f = e.fra_frame(a.fra, base, cols, pool)
keys = [f"FRA|{c['id']}" for c in fra]
for src, names in ((c5.C4DIR / 'c4_features.csv.gz', c5.C4_NUM + c5.C4_ROLE), (c5.HERE / 'c5_features.csv.gz', c5.TAGC + c5.SCALE + c5.CNT),
                   (R / 'c9_power_questions/c9_features.csv.gz', c9.MEAN + c9.SD + c9.SUM)):
    tb = pd.read_csv(src).set_index('key')
    for c in names:
        f[c] = tb.loc[keys, c].to_numpy(dtype=float)
miss = [c for c in lab if c not in f.columns]
assert not miss, miss
cards = {k: v for k, v in zip(keys, vec(f))}

# TRK: labels by card name (label/cards.csv.gz), same construction as export_b10.py
gal = json.loads(gzip.open(a.trk, 'rt', encoding='utf-8').read())['cards']
q = pd.read_csv(t.LAB / 'cards.csv.gz', keep_default_na=False)
byname = {}
for r in q.itertuples():
    byname.setdefault(t.norm_name(r.name), r)
raws = {p: d for p, (d, bad) in t.load_all().items()}
rows, have = [], []
for c in gal:
    r = byname.get(t.norm_name(c['name']))
    if r is not None and (r.auto or all(r.id in raws[p] for p in t.PASSES)):
        rows.append(r); have.append(c)
t3, t4, t5, t9 = t.label_tables(rows, raws)
x = pd.DataFrame([r.auto == 1 and [0] * 10 + ['-'] or raws['c3'][r.id] for r in rows], columns=c3.FIELDS + ['dep'])
tmp = HERE / 'export_tmp'; tmp.mkdir(exist_ok=True)
c3path = tmp / 'c3_trk_labels.csv.gz'
pd.concat([pd.DataFrame({'key': [f"TRK|{c['id']}" for c in have]}), x, t3], axis=1).to_csv(c3path, index=False, compression='gzip')
trk_cards, ft = e.fra_frame(a.trk, base, cols, pool, 'TRK', c3path) if False else (None, None)
ft = t3.copy()
for tab in (t4, t5, t9):
    for c in tab.columns:
        ft[c] = tab[c].to_numpy(dtype=float)
miss = [c for c in lab if c not in ft.columns]
assert not miss, miss
cards.update({f"TRK|{c['id']}": v for c, v in zip(have, vec(ft))})
out = {'version': 'similar-labels-28pool-20261022', 'dims': lab, 'scale': 1000, 'refs': ref_out, 'cards': cards}
with gzip.open(a.out, 'wt', encoding='utf-8') as fh:
    json.dump(out, fh, separators=(',', ':'))
print({'dims': len(lab), 'refs': len(ref_out), 'ref_total': len(refs), 'fra': sum(k.startswith('FRA') for k in cards), 'trk': sum(k.startswith('TRK') for k in cards), 'trk_gallery': len(gal)})
