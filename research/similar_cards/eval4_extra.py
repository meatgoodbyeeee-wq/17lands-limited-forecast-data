#!/usr/bin/env python3
"""Exploratory (no pre-registered criterion): do the 707 name_only references help or hurt "similar cards" accuracy when they are added as candidates?
Same frame as eval2.py / eval3_c9zero.py: production similarity from the site code, 4,919 pool cards as targets (>= 3000 games), candidates from OTHER sets only,
GIH centred per set, similar = mean of the top 3 of (production cos + 0.5 x label cos) with the class / mana-value-within-2 filter.
Extras: name_only cards with label vectors (C9 neutral) and their own GIH (17Lands, centred with the pool's set mean).
  python3 eval4_extra.py <dir with mat.f32 + keys.json (node dump_prod_sim_extra.mjs over refs + extras)> <extra.json from export_extra_labels.py --dump> 
"""
import sys, json, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
D, XJ = sys.argv[1], sys.argv[2]; sys.argv = ['x']
exec(open('eval.py').read().split('ERR = {}')[0])   # pool, L (L2 of std pool labels), cls, mv, gc, sets, ok, lab, gih ...
keys = json.load(open(f'{D}/keys.json')); N = len(keys)
P = np.fromfile(f'{D}/mat.f32', dtype=np.float32).reshape(N, N)
ext = json.load(open(XJ))
pk = {(s, n): i for i, (s, n) in enumerate(zip(pool.set, pool.name))}
fn = lambda n: n.split(' // ')[0].strip().lower()
setmean = pd.Series(gih).groupby(pool.set.to_numpy()).mean().to_dict()
tl = lambda t: 0 if 'land' in (t or '').lower() else (1 if 'creature' in (t or '').lower() else 2)

# targets / main candidates: pool cards among the references with >= 3000 games
m = [(a, pk.get((k[0], k[1]))) for a, k in enumerate(keys) if k[2] == 0]
m = [(a, i) for a, i in m if i is not None and ok[i]]
A = np.array([a for a, _ in m]); I = np.array([i for _, i in m])
# extras
xa = [a for a, k in enumerate(keys) if k[2] == 1]
XA = np.array(xa); xk = [keys[a] for a in xa]
Lx = np.array([ext[f'{k[0]}|{k[1]}'] for k in xk], float) / 1000.0
Lx /= np.linalg.norm(Lx, axis=1, keepdims=True) + 1e-9
x_set = np.array([k[0] for k in xk]); x_cls = np.array([tl(k[3]) for k in xk]); x_mv = np.array([float(k[4] or 0) for k in xk])
x_gc = np.array([k[5] * (100 if k[5] <= 1 else 1) - setmean.get(k[0], np.nan) for k in xk])
x_n = np.array([k[6] for k in xk]); x_n = np.where(np.isnan(x_gc), -1, x_n);  # sets without a pool mean (MH3) cannot be centred: left out of this evaluation
x_name = np.array([fn(k[1]) for k in xk])
print('extras', len(xk), 'sets missing in pool', sorted(set(x_set) - set(setmean)), 'gih range', np.nanmin(x_gc), np.nanmax(x_gc))
name = np.array([fn(n) for n in pool.name])
T = dict(set=sets[I], cls=cls[I], mv=mv[I], gc=gc[I], name=name[I])

def run(w, filt, use_x, xmin, nosame, Lc_neutral=None, Lt=None):
    Lt_ = L[I] if Lt is None else Lt
    Lc_main = L[I] if Lc_neutral is None else Lc_neutral
    S = P[np.ix_(A, A)] + w * (Lt_ @ Lc_main.T)
    set_c, cls_c, mv_c, gc_c, nm_c = T['set'], T['cls'], T['mv'], T['gc'], T['name']
    if use_x:
        sel = np.where((x_n >= xmin) & (x_n >= 0))[0]
        Sx = P[np.ix_(A, XA[sel])] + w * (Lt_ @ Lx[sel].T)
        S = np.hstack([S, Sx])
        set_c = np.r_[set_c, x_set[sel]]; cls_c = np.r_[cls_c, x_cls[sel]]; mv_c = np.r_[mv_c, x_mv[sel]]; gc_c = np.r_[gc_c, x_gc[sel]]; nm_c = np.r_[nm_c, x_name[sel]]
    S = S.copy()
    S[T['set'][:, None] == set_c[None, :]] = -9
    if nosame: S[T['name'][:, None] == nm_c[None, :]] = -9
    if filt: S[(T['cls'][:, None] != cls_c[None, :]) | (np.abs(T['mv'][:, None] - mv_c[None, :]) > 2)] = -9
    top = np.argsort(-S, 1)[:, :3]
    pred = gc_c[top].mean(1); e = np.abs(pred - T['gc'])
    nx = (top >= len(I)).sum()
    return e, pred, dict(n=len(I), mae=e.mean(), r=np.corrcoef(pred, T['gc'])[0, 1], rmse=np.sqrt(((pred - T['gc']) ** 2).mean()), extra_slots=int(nx),
                        cards_with_extra=int(((top >= len(I)).any(1)).sum()), top=top)
rows = []
def rec(label, w, filt, use_x, xmin, nosame, **kw):
    e, pred, d = run(w, filt, use_x, xmin, nosame, **kw); top = d.pop('top'); d['arm'] = label; rows.append(d); return e, pred, top
b0 = rec('old: production cos only, main refs', 0, 0, 0, 0, 0)
rec('(eval2 repro) production + 0.5 x labels + filters, main refs', .5, 1, 0, 0, 0)
print(pd.DataFrame(rows).round(3).to_string(index=False))
res = {}
for nosame in (0, 1):
    tag = 'same-name excluded' if nosame else 'same-name allowed (eval2 frame)'
    e0, p0, t0 = rec(f'main refs only [{tag}]', .5, 1, 0, 0, nosame)
    e1, p1, t1 = rec(f'+ extras with >=3000 games [{tag}]', .5, 1, 1, 3000, nosame)
    e2, p2, t2 = rec(f'+ all 707 extras (>=500 games, as on the site) [{tag}]', .5, 1, 1, 0, nosame)
    for lab_, e_, t_ in (('>=3000', e1, t1), ('all707', e2, t2)):
        d = e_ - e0; ch = (t_ != t0).any(1) if False else None
        rng = np.random.default_rng(0); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        res[(tag, lab_)] = (d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5), (d < 0).mean(), (d > 0).mean())
df = pd.DataFrame(rows).round(3); print(); print(df.to_string(index=False)); df.to_csv('eval4_extra_results.csv', index=False)
print(); print('paired change in per-card absolute error, extras minus main (pp; negative = better), 95% bootstrap CI, share better / worse')
for k, v in res.items(): print(k, 'mean %.3f CI [%.3f, %.3f] better %.3f worse %.3f' % v)
# sensitivity: what does a neutral C9 cost when it is applied to a random 495 / 707 of the pool candidates? (same candidates, same targets)
c9i = [i for i, c in enumerate(lab) if c.startswith('c9_m_')]; assert len(c9i) == 7
X = pool[lab].fillna(0).to_numpy(float); Zs = (X - X.mean(0)) / (X.std(0) + 1e-9)
out = []
for k in (495, 707):
    for seed in range(5):
        rng = np.random.default_rng(seed); pick = rng.choice(len(I), k, replace=False)
        Zc = Zs[I].copy(); Zc[np.ix_(pick, c9i)] = 0; Zc /= np.linalg.norm(Zc, axis=1, keepdims=True) + 1e-9
        e, p, d = run(.5, 1, 0, 0, 1, Lc_neutral=Zc); d.pop('top'); out.append((k, seed, d['mae'], d['r']))
e, p, d = run(.5, 1, 0, 0, 1); d.pop('top')
print('\nsensitivity: random k pool CANDIDATES get neutral C9 (main refs only, same-name excluded); baseline mae %.3f r %.3f' % (d['mae'], d['r']))
o = pd.DataFrame(out, columns=['k', 'seed', 'mae', 'r']).groupby('k').mean().round(3); print(o)
