#!/usr/bin/env python3
"""Score similar-card selection variants (PLAN.md). python3 eval.py [prod_neighbours.csv]"""
import sys, json, itertools, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
HERE = Path(__file__).resolve().parent; R = HERE.parents[0]
sys.path.insert(0, str(R / 'c9_power_questions')); sys.path.insert(0, str(R / 'gih_llm_extract'))
import c9  # noqa
pool, base, cols = c9.load_pool()
pool = pool.reset_index(drop=True)
MIN = 3000
def l2(x): return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-9)
def std(df): 
    a = df.to_numpy(float); return (a - a.mean(0)) / (a.std(0) + 1e-9)
txt = [(t if isinstance(t,str) else '').replace(n, 'CARD').lower() + ' ' + (ty if isinstance(ty,str) else '').lower() for t, n, ty in zip(pool.oracle_text, pool.name, pool.type_line)]
T = l2(TfidfVectorizer(token_pattern=r'[a-z]{2,}', sublinear_tf=True, min_df=2).fit_transform(txt).toarray())
bcols = ['mv','rarity_ord','n_colors','mana_symbols','power','toughness','type_creature','type_instant','type_sorcery','type_artifact','type_enchantment','type_planeswalker','type_land','is_multicolor']
B = l2(std(pool[bcols].fillna(0)))
lab = [c for c in pool.columns if c.startswith(('c4_','c5_')) and pool[c].dtype != object] + [c for c in pool.columns if c.startswith('c9_m_')] + [c for c in cols if c in pool.columns]
lab = list(dict.fromkeys(lab)); L = l2(std(pool[lab].fillna(0)))
tl = pool.type_line.fillna('').str.lower()
cls = np.where(tl.str.contains('land'), 0, np.where(tl.str.contains('creature'), 1, 2))
mv = pool.mv.fillna(0).to_numpy(float)
sets = pool.set.to_numpy(); gih = pool.actual_gih.to_numpy(float)*100
gc = gih - pd.Series(gih).groupby(pool.set).transform('mean').to_numpy()
ok = (pool.gih_games >= MIN).to_numpy()
idx = np.where(ok)[0]

ERR = {}
def run(wt, wb, wl, filt, cand_sets=None):
    X = np.hstack([wt*T, wb*B, wl*L]); X = l2(X)
    S = X[idx] @ X[idx].T
    n = len(idx); s = sets[idx]
    bad = s[:, None] == s[None, :]
    if cand_sets is not None: bad |= ~np.isin(s, cand_sets)[None, :]
    if filt: bad |= (cls[idx][:, None] != cls[idx][None, :]) | (np.abs(mv[idx][:, None] - mv[idx][None, :]) > 2)
    S[bad] = -9
    top = np.argsort(-S, 1)[:, :3]
    nb = idx[top]
    pred = gc[nb].mean(1); own = gc[idx]
    valid = (np.take_along_axis(S, top, 1) > -5).all(1)
    err = np.abs(pred - own)[valid]
    full = np.full(len(pool), np.nan); full[idx[valid]] = err; ERR[(wt,wb,wl,filt,tuple(cand_sets) if cand_sets else None)] = full
    return dict(mae=err.mean(), r=np.corrcoef(pred[valid], own[valid])[0, 1], same_class=(cls[nb] == cls[idx][:, None]).mean(), mv_diff=np.abs(mv[nb] - mv[idx][:, None]).mean(), n=int(valid.sum()))
res = []
V = {'T': (1, .5, 0), 'TL': (1, .5, 1), 'L': (.5, .5, 1), 'LL': (0, .5, 1)}
old22 = [s for s in sorted(set(sets)) if s not in ('EOE','TLA','ECL','TMT','SOS','MSH','HOB')]
for k, w in V.items():
    for f in (0, 1):
        res.append(dict(variant=k, filters=f, cands='28', **run(*w, f)))
for k in ('T', 'TL', 'L', 'LL'):
    res.append(dict(variant=k, filters=0, cands='22', **run(*V[k], 0, old22)))
# baseline for reference: neighbours chosen at random among other sets (expected error), and rarity-only
rng = np.random.default_rng(0)
r0 = []
for i in idx:
    c = rng.choice(idx[sets[idx] != sets[i]], 3, replace=False); r0.append(abs(gc[c].mean() - gc[i]))
res.append(dict(variant='random', filters=0, cands='28', mae=np.mean(r0), r=np.nan, same_class=np.nan, mv_diff=np.nan, n=len(idx)))
if len(sys.argv) > 1:
    p = pd.read_csv(sys.argv[1]); key = {(s, n): i for i, (s, n) in enumerate(zip(pool.set, pool.name))}
    errs, cl, md = [], [], []
    for r in p.itertuples():
        i = key.get((r.set, r.name))
        nbs = [key.get((r.n1s, r.n1)), key.get((r.n2s, r.n2)), key.get((r.n3s, r.n3))]
        if i is None or not ok[i] or any(j is None or not ok[j] for j in nbs): continue
        errs.append(abs(np.mean([gc[j] for j in nbs]) - gc[i])); cl.append(np.mean([cls[j] == cls[i] for j in nbs])); md.append(np.mean([abs(mv[j]-mv[i]) for j in nbs]))
    sub = np.full(len(pool), False); 
    for r in p.itertuples():
        i = key.get((r.set, r.name)); nbs = [key.get((r.n1s, r.n1)), key.get((r.n2s, r.n2)), key.get((r.n3s, r.n3))]
        if i is not None and ok[i] and all(j is not None and ok[j] for j in nbs): sub[i] = True
    for k, w in V.items():
        e = ERR[(*w, 0, tuple(old22))]; res.append(dict(variant=k + '_on_prod_subset', filters=0, cands='22', mae=np.nanmean(e[sub]), r=np.nan, same_class=np.nan, mv_diff=np.nan, n=int(sub.sum())))
    res.append(dict(variant='production', filters=0, cands='22', mae=np.mean(errs), r=np.nan, same_class=np.mean(cl), mv_diff=np.mean(md), n=len(errs)))
df = pd.DataFrame(res).round(3); print(df.to_string(index=False)); df.to_csv(HERE / 'eval_results.csv', index=False)
