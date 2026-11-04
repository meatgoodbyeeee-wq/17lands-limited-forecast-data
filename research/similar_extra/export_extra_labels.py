#!/usr/bin/env python3
"""Label vectors for the 707 "name_only" references (17Lands-measured cards that were outside the 5,611-card reference pool),
appended to an existing data/similar-labels.json.gz as extra `refs` entries.

  python3 export_extra_labels.py --refs <pages>/data/similar-references.json.gz --labels <pages>/data/similar-labels.json.gz --out <new similar-labels.json.gz>

C3/C4/C5 labels come from label/raw (made blind: name -> "~", no set/rarity/numbers, no 17Lands outcomes; see README in label/).
C9 is not labelled: the 7 c9_m columns are set to the 28-set pool mean (= 0 after standardising), same as export_trk_labels.py.
Same 122 columns, same 28-set pool mean/std and standardise -> L2 -> x1000 integer construction as export_labels.py.
The existing file is spliced as text: version, dims, every existing refs entry and every `cards` entry stay byte-identical.
Key = "<set>|<name>" like the existing refs (set/name as in name_only). Refs are never the *target* card, so nothing is added to `cards`.
"""
import argparse, gzip, json, sys, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; R = HERE.parents[0]
for p in ('c9_power_questions', 'gih_llm_extract', 'trk_preview'):
    sys.path.insert(0, str(R / p))
import c9, c3_research as c3, trk_label as t, sonnet_check as sc  # noqa

ap = argparse.ArgumentParser()
for k in ('refs', 'labels', 'out'):
    ap.add_argument('--' + k, type=Path, required=True)
ap.add_argument('--dump', type=Path, help='also write {key: vector} json here (for evaluation)')
a = ap.parse_args()

LAB = HERE / 'label'
q = pd.read_csv(LAB / 'cards.csv', keep_default_na=False)
q['mv'] = pd.to_numeric(q['mv'])

def load(p):
    d, bad = {}, []
    for f in sorted((LAB / 'raw').glob(f'c*_{p}.txt')):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            r = sc.parse(p, line)
            if r is None or r[0] in d:
                bad.append(f'{f.name}:{n} {line!r}'); continue
            d[r[0]] = r[1]
    assert not bad, bad[:5]
    return d
raws = {p: load(p) for p in ('c3', 'c4', 'c5')}
need = set(q.loc[q.auto == 0, 'id'])
labelled = [r for r in q.itertuples() if r.auto == 1 or all(r.id in raws[p] for p in raws)]
missing = len(q) - len(labelled)

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

t3, t4, t5, _ = t.label_tables(labelled, raws, with_c9=False)
ft = t3.copy()
for tab in (t4, t5):
    for c in tab.columns:
        ft[c] = tab[c].to_numpy(dtype=float)
for i in c9i:
    ft[lab[i]] = mu[i]
miss = [c for c in lab if c not in ft.columns]
assert not miss, miss
Z = (ft[lab].fillna(0).to_numpy(float) - mu) / sd
assert np.allclose(Z[:, c9i], 0)
Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
V = np.rint(Z * 1000).astype(int).tolist()
new = {r.key: v for r, v in zip(labelled, V)}
assert len(new) == len(labelled), 'duplicate keys among the extra cards'
dup = [k for k in new if k in old['refs']]
assert not dup, f'keys already in refs: {dup[:5]}'

# splice into the refs object: ...,"refs":{...},"cards":{...}}
mark = '},"cards":{'
assert old_text.count(mark) == 1 and list(old.keys()) == ['version', 'dims', 'scale', 'refs', 'cards']
i = old_text.index(mark)
add = ','.join(json.dumps(k, ensure_ascii=False) + ':' + json.dumps(v, separators=(',', ':')) for k, v in new.items())
out_text = old_text[:i] + ',' + add + old_text[i:]
chk = json.loads(out_text)
assert all(chk['refs'][k] == v for k, v in old['refs'].items()) and chk['cards'] == old['cards'] and chk['dims'] == old['dims']
assert list(chk['refs'])[:len(old['refs'])] == list(old['refs'])
with gzip.GzipFile(a.out, 'wb', mtime=0) as fh:
    fh.write(out_text.encode('utf-8'))
if a.dump:
    a.dump.write_text(json.dumps(new))
print({'name_only': len(q), 'auto': int((q.auto == 1).sum()), 'labelled': len(new), 'unlabelled': missing, 'dims': len(lab),
       'refs_before': len(old['refs']), 'refs_after': len(chk['refs']), 'cards': len(chk['cards'])})
