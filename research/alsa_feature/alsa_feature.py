"""Improvement 2: ALSA predictions as GIH features, Rule L (see PLAN.md, pre-registered).

  python3 research/alsa_feature/alsa_feature.py
"""
import itertools, json, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'research/production_c3'))
import export_adopted_alsa as ea  # noqa: E402
import export_gih_c3_28set as e   # noqa: E402

COLS = list('WUBRG')
SEED = 20260922
ARGS = dict(loss='squared_error', max_iter=250, learning_rate=0.06, l2_regularization=2, random_state=20260923)


def alsa_table():
    f = pd.read_csv(ROOT / 'data/features/dev_feature_22.csv.gz')
    y = pd.read_csv(HERE / 'data/dev_alsa_actuals.csv')
    assert 'FIN' not in set(f['set']) | set(y['set'])
    y = y.drop_duplicates(['set', 'name'])   # 5 duplicated KHM snow-land rows; the adopted script kept both
    d = f.merge(y, on=['set', 'name'], how='inner', validate='one_to_one')
    d = d[d['set'] != 'MH3'].reset_index(drop=True)
    base = [c for c in d.columns if c not in ea.DROP | ea.NON_NUMERIC and pd.api.types.is_numeric_dtype(d[c])]
    rar = pd.get_dummies(d.get('rarity', pd.Series('unknown', index=d.index)).fillna('unknown').astype(str), prefix='rarity', dtype=float).columns.tolist()
    x = ea.features(d, base, rar)
    return d, x


def fit_pred(x, y, tr, te):
    m = make_pipeline(SimpleImputer(strategy='median'), HistGradientBoostingRegressor(**ARGS))
    m.fit(x[tr], y[tr])
    return m.predict(x[te])


def nested_alsa(d, x):
    """out[(s, t)] -> ALSA predictions of set t from a model trained without s and t ('held' = without s only, t == s)."""
    sets = sorted(d['set'].unique())
    y = d['actual_alsa'].values
    sv = d['set'].values
    out = {}
    for s in sets:
        out[(s, s)] = fit_pred(x, y, sv != s, sv == s)
        print('alsa', s, flush=True)
    for s, t in itertools.combinations(sets, 2):
        tr = (sv != s) & (sv != t)
        p = fit_pred(x, y, tr, (sv == s) | (sv == t))
        out[(s, t)] = p[(sv[(sv == s) | (sv == t)] == t)]   # t's prediction in a model without s,t
        out[(t, s)] = p[(sv[(sv == s) | (sv == t)] == s)]   # s's prediction in a model without s,t
    return out


def build_xfeat(g, a):
    """g: cards of one set (pool rows), a: predicted ALSA (aligned). Returns X1-X4 as DataFrame."""
    cm = g[[f'color_{c}' for c in COLS]].values.astype(float)
    cm[g['type_land'].values == 1] = 0
    n = cm.sum(1)
    cu = (g['rarity_ord'].values <= 1)
    mono = (cm.sum(1) == 1)
    mc = np.array([a[cu & mono & (cm[:, i] == 1)].mean() if (cu & mono & (cm[:, i] == 1)).any() else a.mean() for i in range(5)])
    own = np.where(n > 0, (cm * mc).sum(1) / np.maximum(n, 1), 0.0)
    pop = np.where(n > 0, (cm * (mc - mc.mean())).sum(1) / np.maximum(n, 1), 0.0)
    X1 = a - a.mean()
    X2 = np.where(n > 0, a - own, 0.0)
    X4 = pd.Series(a).groupby(g['rarity_ord'].values).rank(pct=True).values
    return pd.DataFrame({'X1': X1, 'X2': X2, 'X3': pop, 'X4': X4}, index=g.index)


def main():
    t0 = time.time()
    d, x = alsa_table()
    sets = sorted(d['set'].unique())
    assert len(sets) == 21, sets
    cache = HERE / 'alsa_nested.pkl'
    if cache.exists():
        nested = pd.read_pickle(cache)
    else:
        nested = nested_alsa(d, x)
        pd.to_pickle(nested, cache)
    print('alsa done', time.time() - t0, flush=True)
    key = {s: d.loc[d['set'] == s, 'name'].values for s in sets}

    pool, base, cols = e.training()
    pool = pool[pool['set'].isin(sets)].reset_index(drop=True)
    nums = base + cols
    # attach nested ALSA predictions (per ordered pair) as columns computed per fold
    names_ok = all(set(pool.loc[pool['set'] == s, 'name']) <= set(key[s]) for s in sets)
    cover = {s: float(pool.loc[pool['set'] == s, 'name'].isin(key[s]).mean()) for s in sets}
    print('coverage min', min(cover.values()), 'names_ok', names_ok, flush=True)

    def alsa_for(s_holdout, t):
        p = pd.Series(nested[(s_holdout, t)], index=key[t])
        g = pool[pool['set'] == t]
        return g, p.reindex(g['name']).values

    arms = {'A': [], 'B': ['X1', 'X2', 'X3', 'X4'], 'B_X3': ['X3'], 'B_X1': ['X1']}
    preds = {k: np.full(len(pool), np.nan) for k in arms}
    imps = []
    for s in sets:
        feats = []
        for t in sets:
            g, a = alsa_for(s, t)
            a = np.where(np.isnan(a), np.nanmean(a), a)
            feats.append(build_xfeat(g, a))
        xf = pd.concat(feats).reindex(pool.index)
        tr = pool['set'] != s
        te = ~tr
        for k, add in arms.items():
            P = pd.concat([pool, xf[add]], axis=1) if add else pool
            c, t_, x_ = e.parts(P[tr], P[te], nums + add, SEED)
            preds[k][te.values] = c + 1.25 * (.7 * t_ + .3 * x_ - c)
        print('gih', s, round(time.time() - t0), flush=True)
    pool_out = pool[['set', 'name', 'rarity_ord', 'actual_gih']].copy()
    for k in arms:
        pool_out[k] = preds[k]

    def ev(col):
        per = {}
        for s, g in pool_out.groupby('set'):
            per[s] = {'mae_pp': float((g[col] - g['actual_gih']).abs().mean() * 100),
                      'spearman': float(spearmanr(g[col], g['actual_gih']).correlation)}
        return {'pooled_mae_pp': float((pool_out[col] - pool_out['actual_gih']).abs().mean() * 100),
                'spearman_mean': float(np.mean([v['spearman'] for v in per.values()])), 'per_set': per}
    res = {'sets': sets, 'n_cards': len(pool_out), 'seed': SEED, 'coverage_min': min(cover.values())}
    evs = {k: ev(k) for k in arms}
    for k, v in evs.items():
        res[k] = {kk: vv for kk, vv in v.items() if kk != 'per_set'}
    res['B']['sets_lower_mae'] = int(sum(evs['B']['per_set'][s]['mae_pp'] < evs['A']['per_set'][s]['mae_pp'] for s in sets))
    res['B']['sets_higher_spearman'] = int(sum(evs['B']['per_set'][s]['spearman'] > evs['A']['per_set'][s]['spearman'] for s in sets))
    for k in ['B_X3', 'B_X1']:
        res[k]['sets_lower_mae'] = int(sum(evs[k]['per_set'][s]['mae_pp'] < evs['A']['per_set'][s]['mae_pp'] for s in sets))
    res['by_rarity'] = {}
    for r, g in pool_out.groupby('rarity_ord'):
        res['by_rarity'][int(r)] = {k: float((g[k] - g['actual_gih']).abs().mean() * 100) for k in ['A', 'B']}
    res['rule_l'] = {'mae': res['B']['pooled_mae_pp'] < res['A']['pooled_mae_pp'],
                     'spearman': res['B']['spearman_mean'] > res['A']['spearman_mean'],
                     'sets': res['B']['sets_lower_mae'] >= 12}
    res['rule_l']['pass'] = all(res['rule_l'].values())
    res['per_set'] = {s: {'A': evs['A']['per_set'][s], 'B': evs['B']['per_set'][s]} for s in sets}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    pool_out.round(5).to_csv(HERE / 'oof.csv.gz', index=False, compression='gzip')
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    main()
