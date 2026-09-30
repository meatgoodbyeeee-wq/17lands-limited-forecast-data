"""Case 4: two-stage colour-strength correction. See PLAN.md (pre-registered).

  python3 research/case4_colour/case4_colour.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
COLS = list('WUBRG')
ALPHA, LAM, LAM_SENS = 1.0, 0.5, [0.25, 1.0]


def load():
    import export_gih_c3_28set as e
    pool, _, _ = e.training()
    oof = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    attrs = pool[['set', 'name', 'type_land', 'llm_removal'] + [f'color_{c}' for c in COLS]]
    d = oof.merge(attrs, on=['set', 'name'], how='left', validate='one_to_one')
    assert d['color_W'].notna().all()
    d['ncol'] = d[[f'color_{c}' for c in COLS]].sum(axis=1)
    d['mono'] = np.where(d['ncol'] == 1, d[[f'color_{c}' for c in COLS]].values.argmax(1), -1)
    d.loc[d['type_land'] == 1, 'mono'] = -1
    d['resid'] = d['actual_gih'] - d['pred']
    return d


def colour_table(d):
    rows = []
    for st, s in d.groupby('set'):
        for i, c in enumerate(COLS):
            m = s[s['mono'] == i]
            cu = m[m['rarity_ord'] <= 1]
            rows.append({'set': st, 'colour': c,
                         'f1': cu['pred'].nlargest(5).mean(),
                         'f2': float(((cu['rarity_ord'] == 0) & (cu['llm_removal'] >= 2)).sum()),
                         'f3': cu['pred'].mean(),
                         'target': m['resid'].mean(), 'n': len(m)})
    t = pd.DataFrame(rows)
    for k in ['f1', 'f2', 'f3', 'target']:
        t[k] = t[k] - t.groupby('set')[k].transform('mean')
    return t


def ridge_fit(X, y, alpha):
    return np.linalg.solve(X.T @ X + alpha * np.eye(X.shape[1]), X.T @ y)


def apply(d, corr):
    """corr: DataFrame set, colour, c. Multicolour = mean of its colours; colourless/lands = 0."""
    piv = corr.pivot(index='set', columns='colour', values='c')[COLS]
    C = piv.loc[d['set']].values
    M = d[[f'color_{c}' for c in COLS]].values.astype(float)
    M[d['type_land'].values == 1] = 0
    n = M.sum(1)
    return np.where(n > 0, (C * M).sum(1) / np.maximum(n, 1), 0.0)


def evaluate(d, adj):
    out = {'mae_pp': float(np.mean(np.abs(adj - d['actual_gih'])) * 100)}
    per = {}
    for st, idx in d.groupby('set').groups.items():
        s = d.loc[idx]
        a = adj[d.index.get_indexer(idx)]
        per[st] = {'mae_pp': float(np.mean(np.abs(a - s['actual_gih'])) * 100),
                   'spearman': float(spearmanr(a, s['actual_gih']).correlation)}
    out['spearman_mean'] = float(np.mean([v['spearman'] for v in per.values()]))
    out['per_set'] = per
    return out


def main():
    d = load().reset_index(drop=True)
    t = colour_table(d)
    feats = ['f1', 'f2', 'f3']
    preds, coefs = [], []
    for st in sorted(t['set'].unique()):
        tr, te = t[t['set'] != st], t[t['set'] == st]
        mu, sd = tr[feats].mean(), tr[feats].std(ddof=0)
        b = ridge_fit(((tr[feats] - mu) / sd).values, tr['target'].values, ALPHA)
        coefs.append(b)
        preds.append(te.assign(c=((te[feats] - mu) / sd).values @ b)[['set', 'colour', 'c']])
    corr = pd.concat(preds)
    c_card = apply(d, corr)
    oracle = apply(d, t.rename(columns={'target': 'c'})[['set', 'colour', 'c']])

    base = evaluate(d, d['pred'].values)
    res = {'n_cards': len(d), 'n_sets': d['set'].nunique(), 'alpha': ALPHA, 'lambda': LAM,
           'coef_mean_std_units': dict(zip(feats, np.mean(coefs, 0).round(5).tolist())),
           'stage2_corr_pred_vs_target': float(np.corrcoef(corr['c'], t.sort_values(['set']).set_index(['set', 'colour']).loc[list(zip(corr['set'], corr['colour']))]['target'])[0, 1]),
           'pred': {k: v for k, v in base.items() if k != 'per_set'}, 'adjusted': {}}
    per_sets = {}
    for lam in [LAM] + LAM_SENS:
        ev = evaluate(d, d['pred'].values + lam * c_card)
        wins = sum(ev['per_set'][s]['mae_pp'] < base['per_set'][s]['mae_pp'] for s in base['per_set'])
        res['adjusted'][str(lam)] = {'mae_pp': ev['mae_pp'], 'spearman_mean': ev['spearman_mean'], 'mae_sets_improved': wins}
        per_sets[str(lam)] = ev['per_set']
    ev = evaluate(d, d['pred'].values + oracle)
    res['oracle'] = {'mae_pp': ev['mae_pp'], 'spearman_mean': ev['spearman_mean']}
    m = res['adjusted'][str(LAM)]
    res['rule_c'] = {'mae': m['mae_pp'] < base['mae_pp'], 'spearman': m['spearman_mean'] > base['spearman_mean'],
                     'sets': m['mae_sets_improved'] >= 16}
    res['rule_c']['pass'] = all(res['rule_c'].values())
    res['per_set'] = {s: {'pred': base['per_set'][s], 'adj_0.5': per_sets[str(LAM)][s]} for s in base['per_set']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    t.merge(corr, on=['set', 'colour']).round(5).to_csv(HERE / 'colour_table.csv', index=False)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    main()
