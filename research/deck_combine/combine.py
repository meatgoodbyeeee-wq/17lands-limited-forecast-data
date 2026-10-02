"""Deck colour: combination of rejected ideas, Rule M (see PLAN.md)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/deck_model'))
import deck_model as dm  # noqa: E402

AF = ['A1', 'A2', 'A3', 'A4', 'A5']


def main():
    a = pd.read_csv(ROOT / 'research/archetype_labels/pair_features.csv')
    s = pd.read_csv(ROOT / 'research/draft_sim/sim_pairs.csv')
    s = s[s['variant'] == 'S'][['set', 'pair', 'S']]
    t = a[['set', 'pair', 'F0'] + dm.FEATS + AF + ['y']].merge(s, on=['set', 'pair']).reset_index(drop=True)
    assert len(t) == 260
    t['F0s'] = dm.loso_scale(t, 'F0')
    t['Ss'] = dm.loso_scale(t, 'S')
    t['D'] = dm.loso_ridge(t, dm.FEATS, dm.ALPHA)
    t['A'] = dm.loso_ridge(t, dm.FEATS + AF, dm.ALPHA)
    t['M1'] = t[['F0s', 'D', 'A', 'Ss']].mean(axis=1)
    t['M2'] = t[['D', 'A', 'Ss']].mean(axis=1)
    t['M3'] = dm.loso_ridge(t, dm.FEATS + AF + ['S'], 10.0)
    t['M4'] = dm.loso_ridge(t, dm.FEATS + AF + ['S'], 30.0)
    cols = ['F0s', 'Ss', 'D', 'A', 'M1', 'M2', 'M3', 'M4']
    rho = {c: dm.per_set_rho(t, c) for c in cols}
    res = {c: {'spearman_mean': float(np.mean(list(rho[c].values()))), 'mae_pp': float((t[c] - t['y']).abs().mean()),
               'sets_better_than_F0': int(sum(rho[c][k] > rho['F0s'][k] for k in rho[c]))} for c in cols}
    bar = max(res['D']['spearman_mean'], res['A']['spearman_mean']) + .02
    for c in ['M1', 'M2', 'M3', 'M4']:
        r = res[c]
        r['rule_m'] = {'spearman': r['spearman_mean'] >= bar and r['spearman_mean'] >= res['F0s']['spearman_mean'] + .05,
                       'sets': r['sets_better_than_F0'] >= 15, 'mae': r['mae_pp'] < res['F0s']['mae_pp']}
        r['rule_m']['pass'] = all(r['rule_m'].values())
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    t.round(4).to_csv(HERE / 'combined.csv', index=False)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
