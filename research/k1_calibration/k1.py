"""K1 rarity calibration of B5 (Rule K, see PLAN.md).  python3 k1.py"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import QuantileRegressor, LinearRegression

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
O = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')


def fit(df, kind):
    """returns dict rarity -> (a, b)"""
    p, y, r = df['pred'].to_numpy(), df['actual_gih'].to_numpy(), df['rarity_ord'].to_numpy()
    out = {}
    if kind == 'K0':
        m = QuantileRegressor(quantile=.5, alpha=0, solver='highs').fit(p[:, None], y)
        return {q: (m.intercept_, m.coef_[0]) for q in range(4)}
    for q in range(4):
        k = r == q
        if kind == 'KI':
            out[q] = (float(np.median(y[k] - p[k])), 1.0)
        elif kind == 'K1':
            m = QuantileRegressor(quantile=.5, alpha=0, solver='highs').fit(p[k][:, None], y[k]); out[q] = (m.intercept_, m.coef_[0])
        elif kind == 'K1_OLS':
            m = LinearRegression().fit(p[k][:, None], y[k]); out[q] = (m.intercept_, m.coef_[0])
    return out


def apply(df, par):
    a = df['rarity_ord'].map(lambda q: par[q][0]); b = df['rarity_ord'].map(lambda q: par[q][1])
    return a + b * df['pred']


def metrics(df, col):
    per = {s: {'mae_pp': float((g[col] - g['actual_gih']).abs().mean() * 100),
               'spearman': float(spearmanr(g[col], g['actual_gih']).correlation)} for s, g in df.groupby('set')}
    return {'pooled_mae_pp': float((df[col] - df['actual_gih']).abs().mean() * 100),
            'spearman_mean': float(np.mean([v['spearman'] for v in per.values()]))}, per


def main():
    d = O.copy()
    kinds = ['K1', 'K0', 'KI', 'K1_OLS']
    for k in kinds:
        d[k] = np.nan
        for s in d['set'].unique():
            te = d['set'] == s
            d.loc[te, k] = apply(d[te], fit(d[~te], k)).to_numpy()
    res, per = {}, {}
    res['B5'], per['B5'] = metrics(d, 'pred')
    for k in kinds:
        res[k], per[k] = metrics(d, k)
        res[k]['sets_lower_mae_vs_B5'] = int(sum(per[k][s]['mae_pp'] < per['B5'][s]['mae_pp'] for s in per[k]))
        res[k]['mae_gain_vs_B5_pp'] = res['B5']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    b5, k1 = res['B5'], res['K1']
    r = {'mae': k1['pooled_mae_pp'] < b5['pooled_mae_pp'], 'spearman': k1['spearman_mean'] > b5['spearman_mean'],
         'sets': k1['sets_lower_mae_vs_B5'] >= 15, 'gain': b5['pooled_mae_pp'] - k1['pooled_mae_pp'] > 0.01}
    r['pass'] = all(r.values()); res['rule_k'] = r
    res['by_rarity'] = {int(q): {c: float((g[c] - g['actual_gih']).abs().mean() * 100) for c in ['pred', 'K1']} |
                        {'bias_B5_pp': float((g['actual_gih'] - g['pred']).mean() * 100), 'bias_K1_pp': float((g['actual_gih'] - g['K1']).mean() * 100)}
                        for q, g in d.groupby('rarity_ord')}
    full = fit(d, 'K1')
    res['K1_params_all28'] = {int(q): {'a': float(a), 'b': float(b)} for q, (a, b) in full.items()}
    res['per_set'] = {s: {'B5': per['B5'][s], 'K1': per['K1'][s]} for s in per['K1']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    d.round(6).to_csv(HERE / 'oof_calibrated.csv.gz', index=False, compression='gzip')
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))
    if r['pass']:
        f = pd.read_csv(ROOT / 'research/c5_atomic_effects/fra_frozen_predictions.csv')
        import gzip
        t = json.loads(gzip.open('/home/claude/limited-forecast-pages/data/target.json.gz', 'rt').read())['cards']
        rmap = {c['id']: {'common': 0, 'uncommon': 1, 'rare': 2, 'mythic': 3}.get(c['rarity'], 0) for c in t}
        f['rarity_ord'] = f['id'].map(rmap)
        f['pred_B5_K1'] = apply(f.rename(columns={'pred_B5': 'pred'}), full).to_numpy()
        f.to_csv(HERE / 'fra_frozen_predictions.csv', index=False)
        meta = {'rule': 'Rule K: B5+K1 (per-rarity median-regression calibration fitted on all 28 sets OOF) vs B5, B, A; FRA 28-day GIH WR, cards >= 500 GIH games: MAE, within-set Spearman',
                'params': res['K1_params_all28'], 'sha256': hashlib.sha256((HERE / 'fra_frozen_predictions.csv').read_bytes()).hexdigest()}
        json.dump(meta, open(HERE / 'fra_frozen_predictions.json', 'w'), indent=1)
        print(meta)


if __name__ == '__main__':
    main()
