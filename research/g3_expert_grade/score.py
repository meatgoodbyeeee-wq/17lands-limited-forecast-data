"""Score G3 pilot (PLAN.md). python3 score.py"""
import json, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
H = Path(__file__).resolve().parent; S = ['FRA', 'TMT', 'ECL']; D = {}
for s in S:
    k = pd.read_csv(H/s/'targets_key.csv'); P = []
    for f in sorted((H/s).glob('pass*.json')):
        d = json.load(open(f)); assert len(d) == len(k), f; k[f.stem] = k.tid.map(d).astype(float); P.append(f.stem)
    k['g3'] = k[P].mean(axis=1); k['P'] = [P]*len(k)
    k['y'] = (k.actual_gih - k.actual_gih.mean())*100; k['p'] = (k.pred - k.pred.mean())*100; k['res'] = k.y - k.p
    k['gz'] = (k.g3 - k.g3.mean())/k.g3.std(); D[s] = k
sp = lambda a, b: float(spearmanr(a, b, nan_policy='omit')[0])
out = {}
for s in S:
    k = D[s]; P = k.P.iloc[0]
    out[s] = {'n': len(k), 'sp_G3_actual': sp(k.g3, k.y), 'sp_C9_actual': sp(k.c9_grade, k.y), 'sp_expert_actual': sp(k.expert, k.y),
              'sp_B10_actual': sp(k.p, k.y), 'sp_G3_resid': sp(k.g3, k.res), 'sp_C9_resid': sp(k.c9_grade, k.res),
              'sp_G3_expert': sp(k.g3, k.expert), 'sp_C9_expert': sp(k.c9_grade, k.expert),
              'pass_agree': [sp(k[a], k[b]) for i, a in enumerate(P) for b in P[i+1:]]}
    o = pd.concat([D[t] for t in S if t != s]); X = np.c_[np.ones(len(o)), o.p, o.gz]; c = np.linalg.lstsq(X, o.y, rcond=None)[0]
    yh = c[0] + c[1]*k.p + c[2]*k.gz
    out[s].update({'combo_coef': c.round(3).tolist(), 'mae_B10': float((k.y - k.p).abs().mean()), 'mae_combo': float((k.y - yh).abs().mean()), 'sp_combo': sp(yh, k.y)})
    out[s]['pilot_ok'] = bool(out[s]['sp_G3_actual'] > out[s]['sp_C9_actual'] and out[s]['sp_G3_resid'] > 0.15)
out['pilot_pass'] = sum(out[s]['pilot_ok'] for s in S) >= 2
json.dump(out, open(H/'score.json', 'w'), indent=1)
for s in S: print(s, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in out[s].items()})
print('PILOT PASS' if out['pilot_pass'] else 'PILOT FAIL')
pd.concat(D.values()).drop(columns='P').to_csv(H/'scored.csv.gz', index=False)
