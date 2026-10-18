import json, numpy as np, pandas as pd
from scipy.stats import spearmanr
o = pd.read_csv('research/c9_power_questions/oof_B10.csv.gz')
f5 = pd.read_csv('research/c5_atomic_effects/c5_features.csv.gz')
o['key'] = o.set + '|' + o.name
d = o.merge(f5[['key', 'c5_TK', 'c5_PC', 'c5_ET']], on='key', how='left')
assert d[['c5_TK','c5_PC','c5_ET']].notna().all().all()
d['a'] = (d.actual_gih - d.groupby('set').actual_gih.transform('mean')) * 100
d['p'] = (d.pred - d.groupby('set').pred.transform('mean')) * 100
TAGS, K = ['c5_TK', 'c5_PC', 'c5_ET'], 100
def tagcorr(tr, te, pcol):
    res = tr.a - tr[pcol]; c = {}
    for t in TAGS:
        m = tr[t] > 0; n = m.sum(); c[t] = res[m].mean() * n / (n + K)
    M = np.column_stack([np.where(te[t] > 0, c[t], np.nan) for t in TAGS])
    adj = np.nan_to_num(np.nanmean(np.where(np.isnan(M).all(1)[:, None], 0, M), 1))
    adj = np.where(np.isnan(M).all(1), 0, adj)
    q = te[pcol] + adj
    return q - q.mean(), c
def slope(tr, pcol): return np.polyfit(tr[pcol], tr.a, 1)[0]
d['pT'] = d['pS'] = d['pTS'] = np.nan; params = {}
for s in d.set.unique():
    tr, te = d[d.set != s].copy(), d[d.set == s]
    qT, c = tagcorr(tr, te, 'p'); d.loc[te.index, 'pT'] = qT
    b = slope(tr, 'p'); d.loc[te.index, 'pS'] = b * te.p
    trT = []
    for s2 in tr.set.unique():   # T-corrected training preds, using same 27-set tag params
        x = tr[tr.set == s2]; q, _ = tagcorr(tr, x, 'p'); trT.append(q)
    tr['pT'] = pd.concat(trT); b2 = slope(tr, 'pT'); d.loc[te.index, 'pTS'] = b2 * qT
    params[s] = dict(c={k: round(v, 3) for k, v in c.items()}, b=round(b, 3), bT=round(b2, 3))
def metrics(col):
    e = (d.a - d[col]).abs(); per = e.groupby(d.set).mean()
    sp = np.mean([spearmanr(g.a, g[col])[0] for _, g in d.groupby('set')])
    top = d[d.groupby('set')[col].rank(ascending=False, pct=True) <= 0.10]
    topA = d[d.groupby('set').a.rank(ascending=False, method='first') <= 10]
    rm = d.rarity_ord >= 2
    return dict(mae=e.mean(), spear=sp, per=per, top_pred_res=(top.a - top[col]).mean(),
                top10_actual_res=(topA.a - topA[col]).mean(), mae_rm=e[rm].mean())
base = metrics('p'); out = {}
print(f"B10: MAE {base['mae']:.4f} Spearman {base['spear']:.4f} predTop10% a-p {base['top_pred_res']:+.2f} actualTop10 a-p {base['top10_actual_res']:+.2f} R/M MAE {base['mae_rm']:.4f}")
for arm in ['pT', 'pS', 'pTS']:
    m = metrics(arm); better = int((m['per'] < base['per']).sum()); gain = base['mae'] - m['mae']
    ok = gain > 0 and m['spear'] >= base['spear'] - 0.0005 and better >= 15 and gain > 0.01
    out[arm] = dict(mae=m['mae'], spear=m['spear'], sets_better=better, gain=gain, top_pred_res=m['top_pred_res'],
                    top10_actual_res=m['top10_actual_res'], mae_rm=m['mae_rm'], supported=bool(ok))
    print(f"{arm}: MAE {m['mae']:.4f} (gain {gain:+.4f}) Spearman {m['spear']:.4f} better {better}/28 predTop10% a-p {m['top_pred_res']:+.2f} actualTop10 {m['top10_actual_res']:+.2f} R/M MAE {m['mae_rm']:.4f} -> {'SUPPORTED' if ok else 'not supported'}")
print('b range', min(v['b'] for v in params.values()), max(v['b'] for v in params.values()))
print('tag c (MSH fold)', params['MSH'])
aa = d[(d.set == 'MSH') & (d.name == 'Avengers Assemble!')].index[0]; s = d[d.set == 'MSH']
for col in ['p', 'pT', 'pS', 'pTS']:
    print('AA', col, round(d.loc[aa, col], 2), 'rank', int((s[col] > d.loc[aa, col]).sum() + 1), '/', len(s), 'actual', round(d.loc[aa, 'a'], 2))
json.dump(dict(B10=dict(mae=base['mae'], spear=base['spear']), arms=out, params=params),
          open('research/g2_bias_spread/result.json', 'w'), indent=1, default=float)
d[['set', 'name', 'rarity_ord', 'a', 'p', 'pT', 'pS', 'pTS']].to_csv('research/g2_bias_spread/oof_g2.csv.gz', index=False)
