"""Score G4 pilot (PLAN.md). python3 score.py"""
import json, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
H = Path(__file__).resolve().parent; S = ['FRA', 'TMT', 'ECL']; D = {}
for s in S:
    k = pd.read_csv(H/'keys'/f'{s}.csv'); a = json.load(open(H/s/'adj.json')); assert len(a) == len(k)
    k['adj'] = k.tid.map(a).astype(float); k['y'] = (k.actual_gih - k.actual_gih.mean())*100; k['res'] = k.y - k.p; D[s] = k
out = {}; tot_b = tot_c = n = 0
for s in S:
    k = D[s]; o = pd.concat([D[t] for t in S if t != s]); kk = float((o.adj*o.res).sum()/(o.adj**2).sum())
    yh = k.p + kk*k.adj; top = k.y.rank(ascending=False) <= len(k)//10
    out[s] = {'n': len(k), 'nonzero': int((k.adj != 0).sum()), 'sp_adj_res': float(spearmanr(k.adj, k.res)[0]),
              'sp_adj_res_nonzero': float(spearmanr(k.adj[k.adj != 0], k.res[k.adj != 0])[0]) if (k.adj != 0).sum() > 5 else None,
              'k': kk, 'mae_B10': float((k.y - k.p).abs().mean()), 'mae_combo': float((k.y - yh).abs().mean()),
              'top_mae_B10': float((k.y - k.p)[top].abs().mean()), 'top_mae_combo': float((k.y - yh)[top].abs().mean()),
              'sp_B10': float(spearmanr(k.p, k.y)[0]), 'sp_combo': float(spearmanr(yh, k.y)[0])}
    tot_b += (k.y - k.p).abs().sum(); tot_c += (k.y - yh).abs().sum(); n += len(k)
out['pooled'] = {'mae_B10': tot_b/n, 'mae_combo': tot_c/n, 'gain': (tot_b - tot_c)/n}
out['pass'] = bool(sum(out[s]['sp_adj_res'] > 0.10 for s in S) >= 2 and out['pooled']['gain'] >= 0.03)
json.dump(out, open(H/'score.json', 'w'), indent=1)
for s in S: print(s, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in out[s].items()})
print(out['pooled'], 'PASS' if out['pass'] else 'FAIL')
pd.concat(D.values()).to_csv(H/'scored.csv.gz', index=False)
