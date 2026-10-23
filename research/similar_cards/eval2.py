#!/usr/bin/env python3
"""Second step of PLAN.md addendum: the production similarity (site code, 22-set reference list) vs production + AI-label block, same cards.
Needs /tmp/prod_mat.f32 and /tmp/prod_keys.json from limited-forecast-pages (node dump of lib/predict.mjs similarity)."""
import sys, json, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
sys.argv = ['x']
exec(open('eval.py').read().split('ERR = {}')[0])   # pool, T, B, L, cls, mv, gc, sets, ok ...
keys = json.load(open('/tmp/prod_keys.json')); N = len(keys)
P = np.fromfile('/tmp/prod_mat.f32', dtype=np.float32).reshape(N, N)
pk = {(s, n): i for i, (s, n) in enumerate(zip(pool.set, pool.name))}
m = [(a, pk.get((s, n))) for a, (s, n) in enumerate(keys)]
m = [(a, i) for a, i in m if i is not None and ok[i]]
A = np.array([a for a, _ in m]); I = np.array([i for _, i in m])          # reference index -> pool index
P = P[np.ix_(A, A)]; Lm = L[I] @ L[I].T; Bm = B[I] @ B[I].T
s_ = sets[I]; c_ = cls[I]; v_ = mv[I]; g_ = gc[I]
same = s_[:, None] == s_[None, :]
def score(S, filt):
    S = S.copy(); S[same] = -9
    if filt: S[(c_[:, None] != c_[None, :]) | (np.abs(v_[:, None] - v_[None, :]) > 2)] = -9
    top = np.argsort(-S, 1)[:, :3]
    e = np.abs(g_[top].mean(1) - g_)
    return dict(n=len(I), mae=e.mean(), r=np.corrcoef(g_[top].mean(1), g_)[0, 1], same_class=(c_[top] == c_[:, None]).mean(), mv_diff=np.abs(v_[top] - v_[:, None]).mean())
res = []
for w in (0, .25, .5, 1, 2):
    for f in (0, 1):
        res.append(dict(variant=f'production + {w} x labels', filters=f, **score(P + w * Lm, f)))
res.append(dict(variant='labels only (L block)', filters=1, **score(Lm, 1)))
df = pd.DataFrame(res).round(3); print(df.to_string(index=False)); df.to_csv('eval2_results.csv', index=False)
