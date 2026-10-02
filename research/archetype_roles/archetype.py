"""Improvement 4: archetype-role features for pair strength, Rule R (see PLAN.md)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/deck_model'))
import deck_model as dm  # noqa: E402
import export_gih_c3_28set as e  # noqa: E402

THEMES = [f'llm_dep_{x}' for x in 'TGAESKCLXHMO']
RF = ['R1', 'R2', 'R3', 'R4', 'R5']


def rfeatures(d):
    rows = []
    for s, g in d.groupby('set'):
        g = g[(g['colors'] != '') & (g['type_land'] != 1)]
        for pair in dm.PAIRS:
            f = g[g['colors'].apply(lambda c: dm.fits(c, pair))]
            w = f['w']
            sh = {t: np.average(f[t] == 1, weights=w) for t in THEMES}
            top = max(sh, key=sh.get)
            gold = f[f['colors'] == pair]
            r5 = f.loc[f[top] == 1, 'pred'].mean() if (f[top] == 1).any() else f['pred'].mean()
            rows.append({'set': s, 'pair': pair, 'R1': sh[top],
                         'R2': np.average(gold['llm_dependency'] >= 1, weights=gold['w']) if len(gold) else 0.0,
                         'R3': np.average(f['llm_net'], weights=w), 'R4': np.average(f['llm_friction'], weights=w), 'R5': r5})
    r = pd.DataFrame(rows)
    for k in RF:
        r[k] = r[k] - r.groupby('set')[k].transform('mean')
    return r


def main():
    pool, _, _ = e.training()
    d = dm.load_cards().merge(pool[['set', 'name', 'llm_dependency', 'llm_net', 'llm_friction'] + THEMES], on=['set', 'name'], validate='one_to_one')
    pw = pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')[['set', 'pair', 'wr_c']].rename(columns={'wr_c': 'y'})
    t = dm.features(d).merge(rfeatures(d), on=['set', 'pair']).merge(pw, on=['set', 'pair']).reset_index(drop=True)
    assert t['set'].nunique() == 26 and len(t) == 260
    t['D'] = dm.loso_ridge(t, dm.FEATS, dm.ALPHA)
    t['R'] = dm.loso_ridge(t, dm.FEATS + RF, dm.ALPHA)
    t['Ronly'] = dm.loso_ridge(t, RF, dm.ALPHA)
    t['F0s'] = dm.loso_scale(t, 'F0')
    for a in dm.ALPHA_SENS:
        t[f'R_a{a}'] = dm.loso_ridge(t, dm.FEATS + RF, a)
    rho = {k: dm.per_set_rho(t, k) for k in ['F0', 'D', 'R', 'Ronly']}
    m = lambda k: float(np.mean(list(rho[k].values())))
    res = {'F0': {'spearman_mean': m('F0'), 'mae_pp': float((t['F0s'] - t['y']).abs().mean())},
           'D': {'spearman_mean': m('D'), 'mae_pp': float((t['D'] - t['y']).abs().mean())},
           'R': {'spearman_mean': m('R'), 'mae_pp': float((t['R'] - t['y']).abs().mean()),
                 'sets_better_than_F0': int(sum(rho['R'][s] > rho['F0'][s] for s in rho['R']))},
           'Ronly': {'spearman_mean': m('Ronly'), 'mae_pp': float((t['Ronly'] - t['y']).abs().mean())},
           'sensitivity': {c: {'spearman_mean': float(np.mean(list(dm.per_set_rho(t, c).values()))), 'mae_pp': float((t[c] - t['y']).abs().mean())}
                           for c in [f'R_a{a}' for a in dm.ALPHA_SENS]},
           'single_feature_spearman': {k: float(np.mean(list(dm.per_set_rho(t, k).values()))) for k in RF}}
    res['rule_r'] = {'spearman': res['R']['spearman_mean'] >= res['F0']['spearman_mean'] + .05 and res['R']['spearman_mean'] >= res['D']['spearman_mean'],
                     'sets': res['R']['sets_better_than_F0'] >= 15, 'mae': res['R']['mae_pp'] < res['F0']['mae_pp']}
    res['rule_r']['pass'] = all(res['rule_r'].values())
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    t.round(4).to_csv(HERE / 'pair_features.csv', index=False)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
