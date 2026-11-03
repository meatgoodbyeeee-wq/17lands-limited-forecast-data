#!/usr/bin/env python3
"""Exploratory (no pre-registered criterion): how much does the similar-card selection lose when the TARGET card's C9 label dimensions are neutral (0)?
Same frame as eval2.py (22-set production similarity from the site code, 4,919 cards, other sets only, GIH centred per set, >= 3000 games).
Candidates keep their full labels (as for TRK: the references are past sets with C9). Only the target's 7 c9_m_* standardised values are set to 0 before L2 normalisation.
  python3 eval3_c9zero.py <dir with prod_mat.f32 and prod_keys.json>
"""
import sys, json, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
D = sys.argv[1]; sys.argv = ['x']
exec(open('eval.py').read().split('ERR = {}')[0])   # pool, L, cls, mv, gc, sets, ok, lab ...
keys = json.load(open(f'{D}/prod_keys.json')); N = len(keys)
P = np.fromfile(f'{D}/prod_mat.f32', dtype=np.float32).reshape(N, N)
pk = {(s, n): i for i, (s, n) in enumerate(zip(pool.set, pool.name))}
m = [(a, pk.get((s, n))) for a, (s, n) in enumerate(keys)]
m = [(a, i) for a, i in m if i is not None and ok[i]]
A = np.array([a for a, _ in m]); I = np.array([i for _, i in m])
P = P[np.ix_(A, A)]
X = pool[lab].fillna(0).to_numpy(float); mu, sdv = X.mean(0), X.std(0) + 1e-9
c9i = [i for i, c in enumerate(lab) if c.startswith('c9_m_')]; assert len(c9i) == 7
Z = (X - mu) / sdv
def q_variant(kind):
    Q = Z.copy()
    if kind == 'neutral': Q[:, c9i] = 0
    if kind == 'raw0': Q[:, c9i] = (0 - mu[c9i]) / sdv[c9i]
    return Q / (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9)
s_ = sets[I]; c_ = cls[I]; v_ = mv[I]; g_ = gc[I]
same = s_[:, None] == s_[None, :]
def score(S, filt):
    S = S.copy(); S[same] = -9
    if filt: S[(c_[:, None] != c_[None, :]) | (np.abs(v_[:, None] - v_[None, :]) > 2)] = -9
    top = np.argsort(-S, 1)[:, :3]
    pred = g_[top].mean(1); e = np.abs(pred - g_)
    return e, dict(n=len(I), mae=e.mean(), r=np.corrcoef(pred, g_)[0, 1], same_class=(c_[top] == c_[:, None]).mean(), mv_diff=np.abs(v_[top] - v_[:, None]).mean())
Lr = L[I]
res, E = [], {}
for name, S, f in (('old: production cos (22 sets), no labels', P, 0),
                   ('new: production + 0.5 x labels + filters, target C9 present', P + .5 * (Lr @ Lr.T), 1),
                   ('new: same, target C9 = 0 (neutral)', P + .5 * (q_variant('neutral')[I] @ Lr.T), 1),
                   ('new: same, target C9 = raw 0 (sensitivity)', P + .5 * (q_variant('raw0')[I] @ Lr.T), 1),
                   ('new: production + 0.5 x labels + filters, all 7 C9 dims dropped on both sides', None, 1)):
    if S is None:
        keep = [i for i in range(len(lab)) if i not in c9i]; Lk = L[:, keep]; Lk = Lk / (np.linalg.norm(Lk, axis=1, keepdims=True) + 1e-9)
        # re-standardising is not needed: columns keep their standardised values
        S = P + .5 * (Lk[I] @ Lk[I].T)
    e, r = score(S, f); E[name] = e; res.append(dict(variant=name, filters=f, **r))
df = pd.DataFrame(res).round(3); print(df.to_string(index=False)); df.to_csv('eval3_c9zero_results.csv', index=False)
# paired differences of per-card error (bootstrap over cards; cards of one set are not independent, so read the interval as rough)
rng = np.random.default_rng(0); names = list(E)
def diff(a, b):
    d = E[a] - E[b]; bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    return d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)
for a, b in ((names[2], names[1]), (names[2], names[0]), (names[1], names[0])):
    print(f'mae({a[:40]}) - mae({b[:40]}): %.3f pp  [95%% boot %.3f, %.3f]' % diff(a, b))
# correlation of the neighbour-mean predictions is reported above (r); share of identical top-3 between C9 present and C9=0
def top3(S, filt):
    S = S.copy(); S[same] = -9
    if filt: S[(c_[:, None] != c_[None, :]) | (np.abs(v_[:, None] - v_[None, :]) > 2)] = -9
    return np.argsort(-S, 1)[:, :3]
t1 = top3(P + .5 * (Lr @ Lr.T), 1); t2 = top3(P + .5 * (q_variant('neutral')[I] @ Lr.T), 1); t0 = top3(P, 0)
print('same top-3 set (C9 present vs C9=0): %.3f; mean overlap of 3: %.2f; overlap new(C9=0) vs old: %.2f' % (np.mean([set(a) == set(b) for a, b in zip(t1, t2)]), np.mean([len(set(a) & set(b)) for a, b in zip(t1, t2)]), np.mean([len(set(a) & set(b)) for a, b in zip(t2, t0)])))
