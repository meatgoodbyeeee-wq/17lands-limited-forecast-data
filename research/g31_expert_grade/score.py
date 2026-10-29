"""G3.1 vs G3 vs C9 (PLAN.md)."""
import json, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
H = Path(__file__).resolve().parent; R = H.parents[1]
b5 = pd.read_csv(R/'research/c5_atomic_effects/oof_B5.csv.gz'); m5 = dict(zip(b5.set+'|'+b5.name, b5.pred))
fr = pd.read_csv(R/'research/c9_power_questions/fra_frozen_predictions.csv'); m5.update({'FRA|'+i: p for i, p in zip(fr.id, fr.pred_B5)})
g3 = pd.read_csv(R/'research/g3_expert_grade/scored.csv.gz').set_index('key').g3
sp = lambda a, b: float(spearmanr(a, b, nan_policy='omit')[0])
out = {}; allk = []
for s in ['FRA', 'TMT', 'ECL']:
    k = pd.read_csv(H/'keys'/f'{s}.csv'); P = []
    for f in sorted((H/s).glob('pass*.json')):
        d = json.load(open(f)); assert len(d) == len(k); k[f.stem] = k.tid.map(d).astype(float); P.append(f.stem)
    k['g31'] = k[P].mean(axis=1); k['g3'] = k.key.map(g3)
    k['y'] = (k.actual_gih - k.actual_gih.mean())*100; k['b5'] = k.key.map(m5); k['r5'] = k.y - (k.b5 - k.b5.mean())*100
    r = {'n': len(k), 'pass_agree': sp(k[P[0]], k[P[1]]) if len(P) > 1 else None}
    for c in ['g31', 'g3', 'c9_grade', 'expert']:
        r[f'b5res_{c}'] = sp(k[c], k.r5); r[f'actual_{c}'] = sp(k[c], k.y)
        for rk, lab in enumerate('CURM'): r[f'{lab}_{c}'] = sp(k[c][k.rarity_ord == rk], k.y[k.rarity_ord == rk])
        r[f'CU_{c}'] = (r[f'C_{c}'] + r[f'U_{c}'])/2
    r['expert_agree_g31'] = sp(k.g31, k.expert); r['expert_agree_g3'] = sp(k.g3, k.expert)
    out[s] = r; allk.append(k.assign(set=s))
a = sum(out[s]['b5res_g31'] > out[s]['b5res_g3'] for s in out)
b = np.mean([out[s]['CU_g31'] for s in out]) - np.mean([out[s]['CU_g3'] for s in out])
out['summary'] = {'sets_b5res_better': int(a), 'CU_gain': float(b), 'pass': bool(a >= 2 and b >= 0.05)}
json.dump(out, open(H/'score.json', 'w'), indent=1); pd.concat(allk).to_csv(H/'scored.csv.gz', index=False)
cols = ['b5res', 'actual', 'C', 'U', 'R', 'M']
for s in ['FRA', 'TMT', 'ECL']:
    print(s, 'agree', round(out[s]['pass_agree'] or 0, 2), 'expert-agree g31/g3', round(out[s]['expert_agree_g31'], 2), round(out[s]['expert_agree_g3'], 2))
    for c in cols: print(f"   {c:7s} G3.1 {out[s][c+'_g31']:+.3f}  G3 {out[s][c+'_g3']:+.3f}  C9 {out[s][c+'_c9_grade']:+.3f}  expert {out[s][c+'_expert']:+.3f}")
print(out['summary'])
