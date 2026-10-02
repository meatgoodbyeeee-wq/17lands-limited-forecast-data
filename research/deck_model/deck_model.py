"""Deck colour step 2: pair-strength model, Rule D (see PLAN.md).

  python3 research/deck_model/deck_model.py
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
PAIRS = ["WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG"]
COLS = "WUBRG"
FEATS = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']
ALPHA, ALPHA_SENS = 3.0, [1.0, 10.0]
RARITY_PACK = {0: 10.0, 1: 3.0, 2: 7 / 8, 3: 1 / 8}


def load_cards():
    import export_gih_c3_28set as e
    pool, _, _ = e.training()
    oof = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    keep = ['set', 'name', 'type_land', 'type_creature', 'mv', 'kw_flying', 'kw_menace', 'llm_removal'] + [f'color_{c}' for c in COLS]
    d = oof.merge(pool[keep], on=['set', 'name'], validate='one_to_one')
    d['colors'] = d.apply(lambda r: ''.join(c for c in COLS if r[f'color_{c}'] == 1), axis=1)
    d = d[~d['type_line'].fillna('').str.contains('Basic')]
    n = d.groupby(['set', 'rarity_ord'])['name'].transform('count')
    d['w'] = d['rarity_ord'].map(RARITY_PACK) / n
    return d


def fits(c, pair):
    return len(c) > 0 and all(x in pair for x in c)


def features(d):
    rows = []
    for s, g in d.groupby('set'):
        med = g['pred'].median()
        g = g[(g['colors'] != '') & (g['type_land'] != 1)]
        for pair in PAIRS:
            e = g[g['colors'].apply(lambda c: fits(c, pair))]
            cu = e[e['rarity_ord'] <= 1]
            w = e['w']
            srt = e.sort_values('pred', ascending=False)
            cum = srt['w'].cumsum()
            top = srt[cum <= srt['w'].sum() / 2]
            if top.empty:
                top = srt.head(1)
            sign = cu[cu['colors'] == pair]
            rows.append({'set': s, 'pair': pair,
                         'F0': cu['pred'].mean(),
                         'F1': np.average(e['pred'], weights=w),
                         'F2': np.average(top['pred'], weights=top['w']),
                         'F3': sign['pred'].mean() if len(sign) else np.nan,
                         'F4': np.average(e['llm_removal'] >= 2, weights=w),
                         'F5': np.average((e['type_creature'] == 1) & (e['mv'] <= 2) & (e['pred'] > med), weights=w),
                         'F6': np.average((e['type_creature'] == 1) & ((e['kw_flying'] == 1) | (e['kw_menace'] == 1)), weights=w)})
    f = pd.DataFrame(rows)
    f['F3'] = f.groupby('set')['F3'].transform(lambda x: x.fillna(x.mean()))
    for k in ['F0'] + FEATS:
        f[k] = f[k] - f.groupby('set')[k].transform('mean')
    return f


def loso_ridge(t, feats, alpha):
    pred = pd.Series(index=t.index, dtype=float)
    for s in t['set'].unique():
        tr, te = t['set'] != s, t['set'] == s
        mu, sd = t.loc[tr, feats].mean(), t.loc[tr, feats].std(ddof=0).replace(0, 1)
        X = ((t.loc[tr, feats] - mu) / sd).values
        b = np.linalg.solve(X.T @ X + alpha * np.eye(len(feats)), X.T @ t.loc[tr, 'y'].values)
        pred[te] = ((t.loc[te, feats] - mu) / sd).values @ b
    return pred


def loso_scale(t, col):
    pred = pd.Series(index=t.index, dtype=float)
    for s in t['set'].unique():
        tr, te = t['set'] != s, t['set'] == s
        x, y = t.loc[tr, col].values, t.loc[tr, 'y'].values
        pred[te] = t.loc[te, col] * (x @ y) / (x @ x)
    return pred


def per_set_rho(t, col):
    return {s: float(spearmanr(g[col], g['y']).correlation) for s, g in t.groupby('set')}


def main():
    cards = load_cards()
    pw = pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')[['set', 'pair', 'wr_c']].rename(columns={'wr_c': 'y'})
    f = features(cards)
    t = f.merge(pw, on=['set', 'pair']).reset_index(drop=True)
    assert t['set'].nunique() == 26 and len(t) == 260, (t['set'].nunique(), len(t))
    t['D'] = loso_ridge(t, FEATS, ALPHA)
    t['F0s'] = loso_scale(t, 'F0')
    for a in ALPHA_SENS:
        t[f'D_a{a}'] = loso_ridge(t, FEATS, a)
    t['D_withF0'] = loso_ridge(t, ['F0'] + FEATS, ALPHA)

    rho0, rhoD = per_set_rho(t, 'F0'), per_set_rho(t, 'D')
    res = {'n_sets': 26,
           'F0': {'spearman_mean': float(np.mean(list(rho0.values()))), 'mae_pp': float((t['F0s'] - t['y']).abs().mean())},
           'D': {'spearman_mean': float(np.mean(list(rhoD.values()))), 'mae_pp': float((t['D'] - t['y']).abs().mean()),
                 'sets_better': int(sum(rhoD[s] > rho0[s] for s in rho0))},
           'zero_prediction_mae_pp': float(t['y'].abs().mean()),
           'single_feature_spearman': {k: float(np.mean(list(per_set_rho(t, k).values()))) for k in ['F0'] + FEATS},
           'sensitivity': {c: {'spearman_mean': float(np.mean(list(per_set_rho(t, c).values()))), 'mae_pp': float((t[c] - t['y']).abs().mean())}
                           for c in [f'D_a{a}' for a in ALPHA_SENS] + ['D_withF0']},
           'per_set': {s: {'F0': rho0[s], 'D': rhoD[s]} for s in rho0}}
    r = res
    r['rule_d'] = {'spearman_gain': r['D']['spearman_mean'] - r['F0']['spearman_mean'] >= 0.05,
                   'sets': r['D']['sets_better'] >= 15, 'mae': r['D']['mae_pp'] < r['F0']['mae_pp']}
    r['rule_d']['pass'] = all(r['rule_d'].values())
    mu, sd = t[FEATS].mean(), t[FEATS].std(ddof=0)
    X = ((t[FEATS] - mu) / sd).values
    r['coef_full_fit_std_units'] = dict(zip(FEATS, np.linalg.solve(X.T @ X + ALPHA * np.eye(6), X.T @ t['y'].values).round(3).tolist()))
    json.dump(r, open(HERE / 'result.json', 'w'), indent=1)
    t.round(4).to_csv(HERE / 'pair_features.csv', index=False)
    print(json.dumps({k: v for k, v in r.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    main()
