"""N2 near-duplicate residual correction (PLAN.md). python3 n2.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prep import *
HERE = Path(__file__).resolve().parent
K = 1; THS = [0.90, 0.95, 0.80]; PRIMARY = 0.90; MINTOK = 6
c, X, v = load()
o = pd.read_csv(C9 / 'oof_B10.csv.gz'); o['key'] = o.set + '|' + o.name
m = pd.DataFrame([(k, i) for i, r in enumerate(c.itertuples()) for k in r.keys.split(';')], columns=['key', 'ci'])
o = o.merge(m, on='key', validate='1:1').merge(c[['cat', 'mv', 'ntok']], left_on='ci', right_index=True).reset_index(drop=True)
o['act'] = o.actual_gih * 100; o['p'] = o.pred * 100
o['r'] = o.act - o.p; o['r'] -= o.groupby('set').r.transform('mean')
Xo = X[o.ci.to_numpy()]; sim = (Xo @ Xo.T).toarray()
A = lambda col: o[col].to_numpy().astype(object)
base_ok = (A('set')[:, None] != A('set')[None, :]) & (A('cat')[:, None] == A('cat')[None, :]) & \
    (np.abs(o.mv.to_numpy()[:, None] - o.mv.to_numpy()[None, :]) <= 1) & (A('name')[:, None] != A('name')[None, :])
tk = (o.ntok.to_numpy() >= MINTOK); base_ok &= tk[:, None] & tk[None, :]
r = o.r.to_numpy(); act = o.act.to_numpy(); p = o.p.to_numpy(); st = A('set')
rng = np.random.default_rng(20261026)
def spear(pr):
    return np.mean([pd.Series(pr[st == s]).corr(pd.Series(act[st == s]), method='spearman') for s in sorted(set(st))])
sp0 = spear(p); mae0 = np.abs(p - act).mean(); out = {}; allcor = {}
for th in THS:
    ok = base_ok & (sim >= th); n = ok.sum(1)
    mean_r = np.where(n > 0, (ok * r[None, :]).sum(1) / np.maximum(n, 1), 0.0)
    corr = n / (n + K) * mean_r; new = p + corr; has = n > 0
    e0 = np.abs(p - act); e1 = np.abs(new - act); d = (e1 - e0)[has]
    bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    res = dict(threshold=th, n_cards=int(has.sum()), n_pairs=int(np.triu(ok | ok.T).sum()), mean_n=float(n[has].mean()),
               mae_corrected_B10=float(e0[has].mean()), mae_corrected_new=float(e1[has].mean()), d_mean=float(d.mean()), ci_lo=float(lo), ci_hi=float(hi),
               pooled_B10=float(e0.mean()), pooled_new=float(e1.mean()), sp_B10=sp0, sp_new=spear(new),
               corr_sd=float(corr[has].std()), corr_mean=float(corr[has].mean()), corr_pred_r=float(np.corrcoef(mean_r[has], (act - p)[has])[0, 1]))
    res['R1'] = res['mae_corrected_new'] < res['mae_corrected_B10']; res['R2'] = res['ci_hi'] < 0
    res['R3'] = res['pooled_new'] <= res['pooled_B10']; res['R4'] = res['sp_new'] - sp0 > -0.0005
    res['pass'] = bool(res['R1'] and res['R2'] and res['R3'] and res['R4']); out[th] = res
    allcor[th] = (has, n, mean_r, corr, new, ok)
    print(json.dumps(res, default=float))
pd.DataFrame(out.values()).to_csv(HERE / 'summary_by_threshold.csv', index=False, float_format='%.4f')
# breakdowns and top pairs at primary
has, n, mean_r, corr, new, ok = allcor[PRIMARY]
d = o.assign(n=n, mean_r=mean_r, corr=corr, new=new, e0=np.abs(p - act), e1=np.abs(new - act))[has].copy(); d['gain'] = d.e0 - d.e1
rar = {0: 'common', 1: 'uncommon', 2: 'rare', 3: 'mythic'}; d['rarity'] = d.rarity_ord.map(rar)
bd = []
for col in ('rarity', 'cat'):
    for kk, g in d.groupby(col): bd.append(dict(by=col, group=kk, n=len(g), mae_B10=g.e0.mean(), mae_new=g.e1.mean(), mean_gain=g.gain.mean(), mean_corr=g['corr'].mean(), mean_err_B10=(g.p - g.act).mean(), mean_err_new=(g.new - g.act).mean()))
BD = pd.DataFrame(bd); BD.to_csv(HERE / 'breakdown.csv', index=False, float_format='%.3f'); print(BD.round(3).to_string())
cols = ['set', 'name', 'rarity', 'cat', 'n', 'act', 'p', 'new', 'corr', 'gain']
d['partners'] = [', '.join(f"{o.at[j,'set']}|{o.at[j,'name']}({r[j]:+.1f},{sim[i,j]:.2f})" for j in np.flatnonzero(ok[i])[:3]) for i in d.index]
d[cols + ['partners']].sort_values('gain', ascending=False).to_csv(HERE / 'corrected_cards_primary.csv', index=False, float_format='%.3f')
print('TOP gain'); print(d.sort_values('gain', ascending=False)[cols + ['partners']].head(10).to_string())
print('TOP loss'); print(d.sort_values('gain')[cols + ['partners']].head(5).to_string())
# Spy Kit / Tricorder ref
i = o.index[(o.set == 'MSH') & (o.name == 'S.H.I.E.L.D. Spy Kit')][0]; print('Spy Kit', o.loc[i, ['p', 'act', 'r']].to_dict(), 'n', n[i], 'corr', corr[i])
# Tricorder reference (text only; no TRK prediction/actual)
t = pd.read_csv('/home/claude/trkwt/research/trk_preview/label/cards.csv.gz', keep_default_na=False); t = t[t.name == 'Tricorder'].iloc[0]
xt = v.transform([norm(t.btext)]); s_t = (xt @ Xo.T).toarray()[0]; tcat = category(t.type_line); ntk = len(re.findall(TOK, norm(t.btext)))
ref = {}
for th in THS:
    mm = (s_t >= th) & (o.cat.to_numpy() == tcat) & (np.abs(o.mv.to_numpy() - t.mv) <= 1) & tk & (ntk >= MINTOK)
    nn = int(mm.sum()); rr = float(r[mm].mean()) if nn else 0.0
    ref[th] = dict(n=nn, mean_r=rr, correction=nn / (nn + K) * rr if nn else 0.0, partners=[f"{o.at[j,'set']}|{o.at[j,'name']}" for j in np.flatnonzero(mm)])
    print('Tricorder', th, ref[th])
el = (o.cat.to_numpy() == tcat) & (np.abs(o.mv.to_numpy() - t.mv) <= 1) & tk
top = np.argsort(-np.where(el, s_t, -1))[:3]; print('Tricorder nearest eligible', [(o.at[j,'set']+'|'+o.at[j,'name'], round(float(s_t[j]),3), round(float(r[j]),2)) for j in top])
print('Tricorder vs Spy Kit cos', float(s_t[i]))
json.dump({'summary': out, 'tricorder_ref': ref}, open(HERE / 'result.json', 'w'), indent=1, default=float)
