"""M1 analysis. python3 -I m1.py   (reads m1_games/normal and m1_games/hybrid next to this file)"""
import sys, os, json, re, glob, unicodedata, random
import numpy as np, pandas as pd
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
NMIN = 100
o = pd.read_csv(HERE + '/../c9_power_questions/oof_B10.csv.gz'); o = o[o.set == 'MSH'].copy()
o['a'] = (o.actual_gih - o.actual_gih.mean()) * 100; o['p'] = (o.pred - o.pred.mean()) * 100; o['res'] = o.a - o.p
o['k'] = o.name.map(norm)
def load(mode):
    G = []
    for f in sorted(glob.glob(f'{HERE}/m1_games/{mode}/job*.json')):
        if f.endswith('.partial.json'): continue
        G += json.load(open(f))
    return G
def obs_of(G):
    rows = []
    for gi, g in enumerate(G):
        if g['winner'] is None: continue
        for dk, cards in g['draws'].items():
            for c in cards: rows.append((norm(c), int(g['winner'] == dk), gi))
    ob = pd.DataFrame(rows, columns=['k', 'w', 'gi']); return ob[ob.k.isin(set(o.k))]
G = {m: load(m) for m in ('normal', 'hybrid')}
OB = {m: obs_of(G[m]) for m in G}
print('games', {m: len(G[m]) for m in G}, 'slow-stopped', {m: sum(g['slow'] for g in G[m]) for m in G},
      'slow rate', {m: round(sum(g['slow'] for g in G[m]) / max(1, len(G[m])), 4) for m in G})
CNT = {m: OB[m].groupby('k').w.agg(['size', 'mean']).rename(columns={'size': 'n', 'mean': 'gih'}) for m in G}
elig = {m: CNT[m][CNT[m].n >= NMIN] for m in G}
common = sorted(set(elig['normal'].index) & set(elig['hybrid'].index) & set(o.k))
print('eligible per mode', {m: len(elig[m]) for m in G}, 'common', len(common), 'of MSH cards', len(o))
D = o[o.k.isin(common)].set_index('k').loc[common].copy()
for m in G:
    gih = CNT[m].loc[common, 'gih']; D['e_' + m] = (gih - gih.mean()) * 100; D['n_' + m] = CNT[m].loc[common, 'n']
def reliability(m):
    rng = random.Random(1); ob = OB[m][OB[m].k.isin(common)]; gis = sorted(ob.gi.unique()); rs = []
    for _ in range(20):
        half = set(rng.sample(gis, len(gis) // 2)); A = ob[ob.gi.isin(half)].groupby('k').w.mean(); B = ob[~ob.gi.isin(half)].groupby('k').w.mean()
        j = A.index.intersection(B.index); r = stats.spearmanr(A[j], B[j])[0]; rs.append(2 * r / (1 + r))
    return float(np.mean(rs))
def loo(cols):
    X = np.c_[np.ones(len(D)), D[cols].values]; y = D.a.values; err = []
    for i in range(len(D)):
        t = np.arange(len(D)) != i; b = np.linalg.lstsq(X[t], y[t], rcond=None)[0]; err.append(abs(y[i] - X[i] @ b))
    return float(np.mean(err))
R = {}
mae_p = loo(['p']); print('LOO MAE p-only (same for both)', round(mae_p, 3))
for m in G:
    e = D['e_' + m]; r1 = stats.spearmanr(e, D.a); r2 = stats.spearmanr(e, D.res)
    rank = e.rank(ascending=False); aa = D[D.name == 'Avengers Assemble!']
    mae_pe = loo(['p', 'e_' + m])
    R[m] = dict(rel=reliability(m), rho_e_a=float(r1[0]), rho_e_res=float(r2[0]), p_res_one=float(r2[1] / 2 if r2[0] > 0 else 1 - r2[1] / 2), mae_pe=mae_pe)
    line = f"[{m}] reliability {R[m]['rel']:.3f}  rho(e,a) {r1[0]:+.3f}  rho(e,res) {r2[0]:+.3f} (one-sided p {R[m]['p_res_one']:.3g})  LOO MAE p+e {mae_pe:.3f}"
    if len(aa):
        x = aa.iloc[0]; R[m]['AA'] = dict(e=float(x['e_' + m]), rank=int(rank[aa.index[0]]), of=len(D), a=float(x.a), p=float(x.p), res=float(x.res))
        line += f"  AA e {x['e_' + m]:+.2f} rank {R[m]['AA']['rank']}/{len(D)} (a {x.a:+.2f} p {x.p:+.2f} res {x.res:+.2f})"
    print(line)
# (5) paired bootstrap over cards for delta rho(e,a)
rng = np.random.default_rng(7); n = len(D); ds = []
eh, ec, a = D.e_hybrid.values, D.e_normal.values, D.a.values
for _ in range(2000):
    ix = rng.integers(0, n, n)
    ds.append(stats.spearmanr(eh[ix], a[ix])[0] - stats.spearmanr(ec[ix], a[ix])[0])
dr = R['hybrid']['rho_e_a'] - R['normal']['rho_e_a']; lo, hi = np.percentile(ds, [2.5, 97.5])
print(f'delta rho(e,a) H-C {dr:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  (bootstrap over cards, 2000)')
# (6) outliers for H
D['gap'] = (D.e_hybrid - D.e_hybrid.mean()) - D.res; t = D.sort_values('gap'); cols = ['name', 'n_hybrid', 'e_hybrid', 'e_normal', 'a', 'p', 'res']
print('--- H: e much lower than res'); print(t[cols].head(10).round(1).to_string(index=False))
print('--- H: e much higher than res'); print(t[cols].tail(10).round(1).to_string(index=False))
slow_rate_h = sum(g['slow'] for g in G['hybrid']) / max(1, len(G['hybrid']))
a_ = lo > 0; b_ = R['hybrid']['mae_pe'] < R['normal']['mae_pe']; c_ = slow_rate_h < 0.05
verdict = 'undetermined' if len(D) < 80 else ('supported' if (a_ and b_ and c_) else 'not supported')
print(f'RULE M1: (a) CI low>0: {a_}  (b) H MAE<C MAE: {b_}  (c) H slow<5%: {c_} ({slow_rate_h:.3%})  -> {verdict}')
json.dump(dict(games={m: len(G[m]) for m in G}, common=len(D), results=R, delta_rho=dr, delta_ci=[float(lo), float(hi)], mae_p=mae_p,
               slow_rate_hybrid=slow_rate_h, a=bool(a_), b=bool(b_), c=bool(c_), verdict=verdict), open(HERE + '/result.json', 'w'), indent=1)
