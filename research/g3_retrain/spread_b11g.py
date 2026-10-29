"""B11gS: Rule F22 arm S (research/g2_bias_spread, branch research/g1-grade-diagnosis) on the B11g OOF.
p' = set mean + b x (B11g - set mean); b for each held-out set fitted on the other 27 sets (a ~ p, set-centred pp, all rarities).
Same four conditions as Rule F22. Writes spread_b11g.json (b on all 28 sets = the factor for TRK if supported).
  python3 research/g3_retrain/spread_b11g.py   (from the repository root)"""
import json, numpy as np, pandas as pd
from scipy.stats import spearmanr
H = 'research/g3_retrain/'
d = pd.read_csv(H + 'oof_B11g.csv.gz')
d['a'] = (d.actual_gih - d.groupby('set').actual_gih.transform('mean')) * 100
d['p'] = (d.pred - d.groupby('set').pred.transform('mean')) * 100
def slope(tr): return np.polyfit(tr.p, tr.a, 1)[0]
d['pS'] = np.nan; bs = {}
for s in d.set.unique():
    tr, te = d[d.set != s], d[d.set == s]
    bs[s] = slope(tr); d.loc[te.index, 'pS'] = bs[s] * te.p
def metrics(col):
    e = (d.a - d[col]).abs(); per = e.groupby(d.set).mean()
    sp = np.mean([spearmanr(g.a, g[col])[0] for _, g in d.groupby('set')])
    top = d[d.groupby('set')[col].rank(ascending=False, pct=True) <= 0.10]
    return dict(mae=e.mean(), spear=sp, per=per, top_pred_res=(top.a - top[col]).mean(), mae_rm=e[d.rarity_ord >= 2].mean())
base, m = metrics('p'), metrics('pS')
better = int((m['per'] < base['per']).sum()); gain = base['mae'] - m['mae']
rule = dict(mae_down=bool(gain > 0), spearman_kept=bool(m['spear'] >= base['spear'] - 0.0005), sets_15=bool(better >= 15), gain_001=bool(gain > 0.01))
out = dict(B11g=dict(mae=base['mae'], spear=base['spear'], top_pred_res=base['top_pred_res'], mae_rm=base['mae_rm']),
           B11gS=dict(mae=m['mae'], spear=m['spear'], top_pred_res=m['top_pred_res'], mae_rm=m['mae_rm'], sets_better=f'{better}/28', gain=gain),
           rule_f22=rule, supported=all(rule.values()), b_all28=float(np.polyfit(d.p, d.a, 1)[0]),
           b_loso_range=[float(min(bs.values())), float(max(bs.values()))])
json.dump(out, open(H + 'spread_b11g.json', 'w'), indent=1, default=float); print(json.dumps(out, indent=1, default=float))
