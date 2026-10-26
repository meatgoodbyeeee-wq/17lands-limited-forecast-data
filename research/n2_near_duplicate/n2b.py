"""N2b (PLAN_N2b.md). python3 n2b.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prep import *
HERE = Path(__file__).resolve().parent
K = 1; MINTOK = 6
c, X, v = load()
o = pd.read_csv(C9 / 'oof_B10.csv.gz'); o['key'] = o.set + '|' + o.name
m = pd.DataFrame([(k, i) for i, r in enumerate(c.itertuples()) for k in r.keys.split(';')], columns=['key', 'ci'])
o = o.merge(m, on='key', validate='1:1').merge(c[['cat', 'mv', 'ntok', 'pt']], left_on='ci', right_index=True).reset_index(drop=True)
o['act'] = o.actual_gih * 100; o['p'] = o.pred * 100
o['r'] = o.act - o.p; o['r'] -= o.groupby('set').r.transform('mean')
Xo = X[o.ci.to_numpy()]; sim = (Xo @ Xo.T).toarray()
A = lambda col: o[col].to_numpy().astype(object)
mv = o.mv.to_numpy(); cat = A('cat'); pt = A('pt')
same = lambda a: a[:, None] == a[None, :]
base = same(cat) & ~same(A('set')) & ~same(A('name'))
tk = o.ntok.to_numpy() >= MINTOK; base &= tk[:, None] & tk[None, :]
mv1 = np.abs(mv[:, None] - mv[None, :]) <= 1
iscr = (cat == 'Creature'); isld = (cat == 'Land')
crit = lambda a: a[:, None]  # row category
def pairs(nc_th, land_th=None):
    ok = np.zeros_like(base)
    cr = base & iscr[:, None] & (sim >= 0.95) & same(mv) & same(pt)
    nc = base & ~iscr[:, None] & ~isld[:, None] & mv1 & (sim >= nc_th)
    ok = cr | nc
    if land_th is not None: ok = base & isld[:, None] & mv1 & (sim >= land_th)
    return ok
ARMS = {'primary': pairs(0.95), 'arm_a_nc090': pairs(0.90), 'arm_b_lands080': pairs(0, 0.80)}
r = o.r.to_numpy(); act = o.act.to_numpy(); p = o.p.to_numpy(); st = A('set')
rng = np.random.default_rng(20261026)
def spear(pr): return np.mean([pd.Series(pr[st == s]).corr(pd.Series(act[st == s]), method='spearman') for s in sorted(set(st))])
sp0 = spear(p); out = {}; store = {}
for nm, ok in ARMS.items():
    n = ok.sum(1); mean_r = np.where(n > 0, (ok * r[None, :]).sum(1) / np.maximum(n, 1), 0.0)
    corr = n / (n + K) * mean_r; new = p + corr; has = n > 0
    e0 = np.abs(p - act); e1 = np.abs(new - act); d = (e1 - e0)[has]
    bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)]); lo, hi = np.percentile(bs, [2.5, 97.5])
    res = dict(arm=nm, n_cards=int(has.sum()), n_pairs=int(np.triu(ok | ok.T).sum()), mean_n=float(n[has].mean()),
               mae_corr_B10=float(e0[has].mean()), mae_corr_new=float(e1[has].mean()), d_mean=float(d.mean()), ci_lo=float(lo), ci_hi=float(hi),
               frac_improved=float((d < 0).mean()), pooled_B10=float(e0.mean()), pooled_new=float(e1.mean()), sp_B10=sp0, sp_new=spear(new),
               corr_sd=float(corr[has].std()), corr_resid=float(np.corrcoef(mean_r[has], (act - p)[has])[0, 1]),
               cards_by_cat={k: int(x) for k, x in pd.Series(cat[has]).value_counts().items()})
    ii, jj = np.nonzero(np.triu(ok | ok.T)); res['pairs_by_cat'] = {k: int(x) for k, x in pd.Series(cat[ii]).value_counts().items()}
    res['R1'] = res['mae_corr_new'] < res['mae_corr_B10']; res['R2'] = res['ci_hi'] < 0
    res['R3'] = res['pooled_new'] <= res['pooled_B10']; res['R4'] = res['sp_new'] - sp0 > -0.0005
    res['pass'] = bool(res['R1'] and res['R2'] and res['R3'] and res['R4']); out[nm] = res; store[nm] = (has, n, corr, new, ok)
    print(json.dumps(res, default=float))
    d_ = o.assign(n=n, corr=corr, new=new, e0=e0, e1=e1)[has].copy(); d_['gain'] = d_.e0 - d_.e1
    d_['partners'] = [', '.join(f"{o.at[j,'set']}|{o.at[j,'name']}({r[j]:+.1f},{sim[i,j]:.2f})" for j in np.flatnonzero(ok[i])[:3]) for i in d_.index]
    cols = ['set', 'name', 'cat', 'n', 'act', 'p', 'new', 'corr', 'gain', 'partners']
    d_[cols].sort_values('gain', ascending=False).to_csv(HERE / f'n2b_cards_{nm}.csv', index=False, float_format='%.3f')
    print('TOP gain'); print(d_.sort_values('gain', ascending=False)[cols].head(6).to_string())
    print('TOP loss'); print(d_.sort_values('gain')[cols].head(6).to_string())
    print(d_.groupby('cat').agg(n=('gain', 'size'), mae0=('e0', 'mean'), mae1=('e1', 'mean')).round(3))
json.dump(out, open(HERE / 'result_n2b.json', 'w'), indent=1, default=float)
