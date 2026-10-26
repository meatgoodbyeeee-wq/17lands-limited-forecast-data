"""EMB1 screen (see PLAN.md). python3 eval_emb1.py"""
import json, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
H = Path(__file__).resolve().parent; C = H.parent / 'c9_power_questions'
RECENT = ['TDM','EOE','SOS','ECL','TLA','MSH','TMT','HOB','DFT','FDN']
u = pd.read_csv(C/'cards.csv.gz', keep_default_na=False)
k2id = {k: r.id for r in u.itertuples() for k in r.keys.split(';')}
o = pd.read_csv(C/'oof_B10.csv.gz'); o['id'] = (o.set+'|'+o.name).map(k2id)
o['y'] = (o.actual_gih - o.groupby('set').actual_gih.transform('mean'))*100
sets = sorted(o.set.unique()); out = {}
def mae(p, g): return float(np.mean(np.abs(p-g.actual_gih))*100)
def wsp(p, g): return float(np.mean([spearmanr(p[g.set==s], g.actual_gih[g.set==s])[0] for s in sets]))
for tag in ['bge', 'mpnet']:
    z = np.load(H/f'emb_{tag}.npz'); idx = {i: j for j, i in enumerate(z['id'])}
    X = np.hstack([z['E'].astype(float)[o.id.map(idx).values], np.eye(4)[o.rarity_ord.values]])
    e = np.zeros(len(o))
    for s in sets:
        tr = (o.set != s).values; te = ~tr; best = None
        for a in [1, 3, 10, 30]:
            err = 0
            for a_i, b_i in GroupKFold(9).split(X[tr], groups=o.set[tr]):
                m = Ridge(alpha=a).fit(X[tr][a_i], o.y[tr].values[a_i])
                err += np.abs(m.predict(X[tr][b_i]) - o.y[tr].values[b_i]).sum()
            best = min(best or (err, a), (err, a))
        e[te] = Ridge(alpha=best[1]).fit(X[tr], o.y[tr]).predict(X[te])
    o['E'] = o.groupby('set').pred.transform('mean') + (e - pd.Series(e).groupby(o.set.values).transform('mean').values)/100
    W = np.round(np.arange(0, .51, .1), 2); blend = np.zeros(len(o)); ws = {}
    for s in sets:
        tr = o.set != s
        w = min(W, key=lambda w: np.abs((1-w)*o.pred[tr] + w*o.E[tr] - o.actual_gih[tr]).mean())
        ws[s] = float(w); te = o.set == s; blend[te] = ((1-w)*o.pred + w*o.E)[te]
    o['blend'] = blend
    per = {s: [mae(o.pred[o.set==s], o[o.set==s]), mae(o.blend[o.set==s], o[o.set==s])] for s in sets}
    rec = o.set.isin(RECENT)
    top = o.groupby('set', group_keys=False).apply(lambda g: g.nlargest(max(1, len(g)//10), 'actual_gih'))
    res = {'E_alone': {'mae': mae(o.E, o), 'wsp': wsp(o.E.values, o)},
           'B10': {'mae': mae(o.pred, o), 'wsp': wsp(o.pred.values, o)},
           'blend': {'mae': mae(o.blend, o), 'wsp': wsp(o.blend.values, o)},
           'sets_improved': int(sum(b < a for a, b in per.values())),
           'recent_mae_B10': mae(o.pred[rec], o[rec]), 'recent_mae_blend': mae(o.blend[rec], o[rec]),
           'top10_under_B10': float((top.actual_gih-top.pred).mean()*100),
           'top10_under_blend': float((top.actual_gih-o.blend[top.index]).mean()*100),
           'w_per_set': ws, 'per_set_mae': per}
    out[tag] = res; o[['set','name','E','blend']].to_csv(H/f'oof_emb1_{tag}.csv.gz', index=False)
    print(tag, json.dumps({k: v for k, v in res.items() if k not in ('per_set_mae','w_per_set')}, indent=1), 'w', sorted(set(ws.values())))
json.dump(out, open(H/'result.json', 'w'), indent=1)
