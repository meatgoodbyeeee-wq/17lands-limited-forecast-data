"""DA1 part B evaluation (Rule DA1). python3 da1_eval.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'c5_atomic_effects'))
import c5
o = pd.read_csv(HERE / 'oof_DA1_raw.csv.gz'); fold = json.load(open(HERE / 'da1_folds.json'))
g = o.groupby('set')
o['mean10'] = g.p10.transform('mean'); o['pc_c'] = o.pred_c - g.pred_c.transform('mean')
o['b'] = o.set.map(lambda s: fold[s]['b']); o['b_in'] = o.set.map(lambda s: fold[s]['b_insample'])
o['pred'] = o.mean10 + o.b * o.pc_c
o['pred_ins'] = o.mean10 + o.b_in * o.pc_c
o['p_b10'] = o.p10
o['pred_ens'] = (o.p10 + o.pred) / 2
arms = {'B10': 'p10', 'DA1': 'pred', 'DA1_insample_slope': 'pred_ins', 'ens_B10_DA1': 'pred_ens'}
res, per = {}, {}
for k, c in arms.items():
    res[k], per[k] = c5.metrics(o.assign(pred=o[c])[['set', 'actual_gih', 'pred']])
for k in arms:
    if k != 'B10':
        res[k]['sets_lower_mae_vs_B10'] = int(sum(per[k][s]['mae_pp'] < per['B10'][s]['mae_pp'] for s in per[k]))
        res[k]['mae_gain_vs_B10_pp'] = res['B10']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
        res[k]['spearman_diff_vs_B10'] = res[k]['spearman_mean'] - res['B10']['spearman_mean']
d, b = res['DA1'], res['B10']
res['rule_da1'] = {'mae_lower': d['pooled_mae_pp'] < b['pooled_mae_pp'], 'spearman_not_lower_by_0.0005': d['spearman_mean'] - b['spearman_mean'] > -0.0005,
                   'sets>=15': d['sets_lower_mae_vs_B10'] >= 15, 'gain>0.01pp': d['mae_gain_vs_B10_pp'] > 0.01}
res['rule_da1']['pass'] = all(res['rule_da1'].values())
res['by_rarity'] = {int(r): {k: float((x[c] - x.actual_gih).abs().mean() * 100) for k, c in arms.items()} | {'n': int(len(x))} for r, x in o.groupby('rarity_ord')}
res['per_set_mae'] = {s: {k: per[k][s]['mae_pp'] for k in arms} for s in per['B10']}
res['per_set_spearman'] = {s: {k: per[k][s]['spearman'] for k in arms} for s in per['B10']}
res['spearman_pred_c_vs_deck_actual_mean'] = float(np.mean([spearmanr(x.pred_c, x.y_c).correlation for _, x in o.groupby('set')]))
res['spearman_pred_c_vs_raw_actual_mean'] = float(np.mean([spearmanr(x.pred_c, x.actual_gih).correlation for _, x in o.groupby('set')]))
res['spearman_B10_vs_deck_actual_mean'] = float(np.mean([spearmanr(x.p10, x.y_c).correlation for _, x in o.groupby('set')]))
res['corr_pred_B10_c_vs_DA1_c'] = float(np.corrcoef(o.p10 - o.mean10, o.pc_c)[0, 1])
res['b_mean'] = float(o.groupby('set').b.first().mean()); res['b_insample_mean'] = float(o.groupby('set').b_in.first().mean())
res['sd_pred_within_set_pp'] = {'B10': float((o.p10 - o.mean10).std() * 100), 'DA1': float((o.pred - o.mean10).std() * 100), 'actual': float((o.actual_gih - o.groupby('set').actual_gih.transform('mean')).std() * 100)}
u = o.assign(err=(o.actual_gih - o.p10) * 100, err_da1=(o.actual_gih - o.pred) * 100).sort_values('err', ascending=False).head(10)
res['top10_underpredicted'] = [{'card': f'{r.set}|{r.name}', 'actual_pp': r.actual_gih * 100, 'B10_pp': r.p10 * 100, 'DA1_pp': r.pred * 100, 'err_B10': r.err, 'err_DA1': r.err_da1,
                               'deck_adj_actual_c_pp': r.y_c * 100} for r in u.itertuples()]
res['top10_mean_abs_err'] = {'B10': float(u.err.abs().mean()), 'DA1': float(u.err_da1.abs().mean())}
json.dump(res, open(HERE / 'result_B.json', 'w'), indent=1, default=float)
print(json.dumps({k: v for k, v in res.items() if k not in ('per_set_mae', 'per_set_spearman')}, indent=1, default=float))
