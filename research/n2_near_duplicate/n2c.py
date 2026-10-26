"""N2c (PLAN_N2c.md). python3 n2c.py n2c_fits.csv.gz   (combined pair fits from the workflow)
Pair definition = n2b.py primary (head of n2b.py is executed unchanged; its residual r is NOT used)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
src = open(HERE / 'n2b.py').read().split("r = o.r.to_numpy()")[0]
exec(compile(src, 'n2b_head', 'exec'))
fits = pd.read_csv(sys.argv[1]).groupby('pair')
ok = ARMS['primary']
act = o.act.to_numpy(); p = o.p.to_numpy(); st = A('set'); nm = A('name')
idx = {(s, n_): i for i, (s, n_) in enumerate(zip(st, nm))}
# partner residual from the model excluding both sets
cache = {}
def resid(sa, sb):
    k = tuple(sorted((sa, sb)))
    if k not in cache:
        f = fits.get_group(f'{k[0]}_{k[1]}').copy(); f['r'] = f.actual_gih * 100 - f.pred * 100
        f['r'] -= f.groupby('set').r.transform('mean'); cache[k] = {(s, n_): r for s, n_, r in zip(f.set, f.name, f.r)}
    return cache[k]
n = ok.sum(1); has = n > 0; mean_r = np.zeros(len(o)); mean_r_old = np.zeros(len(o)); partners = {}
r_old = o.r.to_numpy()
for i in np.flatnonzero(has):
    js = np.flatnonzero(ok[i]); rs = [resid(st[i], st[j])[(st[j], nm[j])] for j in js]
    mean_r[i] = np.mean(rs); mean_r_old[i] = r_old[js].mean()
    partners[i] = ', '.join(f"{st[j]}|{nm[j]}({rj:+.1f}/old {r_old[j]:+.1f},{sim[i,j]:.2f})" for j, rj in list(zip(js, rs))[:3])
corr = n / (n + K) * mean_r; new = p + corr
e0 = np.abs(p - act); e1 = np.abs(new - act); d = (e1 - e0)[has]
rng = np.random.default_rng(20261026)
bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)]); lo, hi = np.percentile(bs, [2.5, 97.5])
def spear(pr): return np.mean([pd.Series(pr[st == s]).corr(pd.Series(act[st == s]), method='spearman') for s in sorted(set(st))])
sp0, sp1 = spear(p), spear(new)
# N2b numbers for comparison (same cards, same formula, old residual)
new_b = p + n / (n + K) * mean_r_old; d_b = (np.abs(new_b - act) - e0)[has]
res = dict(n_cards=int(has.sum()), n_card_pairs=int(np.triu(ok | ok.T).sum()), n_set_pairs=len(cache), mean_n=float(n[has].mean()),
           mae_corr_B10=float(e0[has].mean()), mae_corr_new=float(e1[has].mean()), d_mean=float(d.mean()), ci_lo=float(lo), ci_hi=float(hi),
           frac_improved=float((d < 0).mean()), pooled_B10=float(e0.mean()), pooled_new=float(np.abs(new - act).mean()),
           sp_B10=float(sp0), sp_new=float(sp1), sp_diff=float(sp1 - sp0), corr_sd=float(corr[has].std()),
           corr_resid_new=float(np.corrcoef(mean_r[has], (act - p)[has])[0, 1]), corr_resid_n2b=float(np.corrcoef(mean_r_old[has], (act - p)[has])[0, 1]),
           corr_old_vs_new_partner_resid=float(np.corrcoef(mean_r[has], mean_r_old[has])[0, 1]),
           n2b_check_mae_new=float(np.abs(new_b - act)[has].mean()), n2b_d_mean=float(d_b.mean()),
           sd_partner_resid_new=float(mean_r[has].std()), sd_partner_resid_old=float(mean_r_old[has].std()), tricorder_trk_matches=0, tricorder_correction=0.0)
res['R1'] = bool(res['mae_corr_new'] < res['mae_corr_B10']); res['R2'] = bool(res['ci_hi'] < 0)
res['R3'] = bool(res['pooled_new'] <= res['pooled_B10']); res['R4'] = bool(res['sp_diff'] > -0.0005)
res['pass'] = bool(res['R1'] and res['R2'] and res['R3'] and res['R4'])
g = o.assign(n=n, corr=corr, new=new, e0=e0, e1=e1, partner_resid=mean_r, partner_resid_n2b=mean_r_old)[has].copy(); g['gain'] = g.e0 - g.e1
g['partners'] = [partners[i] for i in g.index]
cols = ['set', 'name', 'cat', 'n', 'act', 'p', 'new', 'corr', 'gain', 'partner_resid', 'partner_resid_n2b', 'partners']
g[cols].sort_values('gain', ascending=False).to_csv(HERE / 'n2c_cards_primary.csv', index=False, float_format='%.3f')
res['by_cat'] = {c: dict(n=int(len(x)), mae_B10=float(x.e0.mean()), mae_new=float(x.e1.mean())) for c, x in g.groupby('cat')}
json.dump(res, open(HERE / 'result_n2c.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90)
print('TOP gain'); print(g.sort_values('gain', ascending=False)[cols].head(8).to_string())
print('TOP loss'); print(g.sort_values('gain')[cols].head(8).to_string())
