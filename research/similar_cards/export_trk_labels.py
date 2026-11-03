#!/usr/bin/env python3
"""TRK label vectors for the "similar cards" re-ranking, added to an existing data/similar-labels.json.gz.

  python3 export_trk_labels.py --trk <pages>/data/trk/target.json.gz --labels <pages>/data/similar-labels.json.gz --out <new similar-labels.json.gz>

Same 122 columns, same 28-set pool mean/std and the same standardise -> L2 -> x1000 integer construction as export_labels.py.
Differences, on purpose:
  * only C3/C4/C5 labels exist for all 336 TRK cards (C9 power questions exist for about 158), so the 7 C9 mean columns are set to the
    pool mean for every TRK card (= 0 after standardising, i.e. neutral and identical for all 336; no mixing of cards with and without C9);
  * the existing file is spliced as text: version, dims, refs and every FRA entry stay byte-identical; only TRK entries are appended.
No outcome (GIH/ALSA) and no human evaluation enters a vector. Needs label/raw from the TRK preview and the 28-set pool (c9.load_pool).
"""
import argparse, gzip, json, sys, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; R = HERE.parents[0]
for p in ('c9_power_questions', 'gih_llm_extract', 'trk_preview'):
    sys.path.insert(0, str(R / p))
import c9, c3_research as c3, trk_label as t  # noqa
ap = argparse.ArgumentParser()
for k in ('trk', 'labels', 'out'):
    ap.add_argument('--' + k, type=Path, required=True)
ap.add_argument('--c9', choices=['neutral', 'raw0'], default='neutral', help='neutral = pool mean (0 after standardising, default); raw0 = raw value 0 (sensitivity only)')
ap.add_argument('--dump', type=Path, help='also write {key: vector} json here (for evaluation)')
a = ap.parse_args()

old_text = gzip.open(a.labels, 'rt', encoding='utf-8').read()
old = json.loads(old_text)
pool, base, cols = c9.load_pool()
pool = pool.reset_index(drop=True)
lab = [c for c in pool.columns if c.startswith(('c4_', 'c5_')) and pool[c].dtype != object] + [c for c in pool.columns if c.startswith('c9_m_')] + [c for c in cols if c in pool.columns]
lab = list(dict.fromkeys(lab))
assert lab == old['dims'], 'dims differ from the existing file'
mu, sd = pool[lab].fillna(0).to_numpy(float).mean(0), pool[lab].fillna(0).to_numpy(float).std(0) + 1e-9
c9i = [i for i, c in enumerate(lab) if c.startswith('c9_m_')]
assert len(c9i) == 7

gal = json.loads(gzip.open(a.trk, 'rt', encoding='utf-8').read())['cards']
q = pd.read_csv(t.LAB / 'cards.csv.gz', keep_default_na=False)
byname = {}
for r in q.itertuples():
    byname.setdefault(t.norm_name(r.name), r)
raws = {p: d for p, (d, bad) in t.load_all().items()}
rows, have = [], []
for c in gal:
    r = byname.get(t.norm_name(c['name']))
    if r is not None and (r.auto or all(r.id in raws[p] for p in t.LABEL_PASSES)):
        rows.append(r); have.append(c)
assert len(have) == len(gal), f'{len(gal) - len(have)} gallery cards without C3/C4/C5 labels'
t3, t4, t5, _ = t.label_tables(rows, raws, with_c9=False)
ft = t3.copy()
for tab in (t4, t5):
    for c in tab.columns:
        ft[c] = tab[c].to_numpy(dtype=float)
for i in c9i:
    ft[lab[i]] = mu[i] if a.c9 == 'neutral' else 0.0
miss = [c for c in lab if c not in ft.columns]
assert not miss, miss
Z = (ft[lab].fillna(0).to_numpy(float) - mu) / sd
assert np.allclose(Z[:, c9i], 0) if a.c9 == 'neutral' else True
Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
V = np.rint(Z * 1000).astype(int).tolist()
new = {f"TRK|{c['id']}": v for c, v in zip(have, V)}
assert len(new) == len(gal) and not any(k in old['cards'] for k in new)

# splice: ...,"cards":{...}}  ->  append entries before the final "}}"
assert old_text.endswith('}}') and list(old.keys())[-1] == 'cards'
add = ','.join(json.dumps(k) + ':' + json.dumps(v, separators=(',', ':')) for k, v in new.items())
out_text = old_text[:-2] + ',' + add + '}}'
json.loads(out_text)
with gzip.GzipFile(a.out, 'wb', mtime=0) as fh:
    fh.write(out_text.encode('utf-8'))
if a.dump:
    a.dump.write_text(json.dumps(new))
print({'trk': len(new), 'auto_cards': int(sum(r.auto for r in rows)), 'c9': a.c9, 'dims': len(lab), 'total_cards': len(old['cards']) + len(new)})
