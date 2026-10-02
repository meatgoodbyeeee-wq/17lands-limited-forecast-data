"""Improvement 1: card-effect target (see PLAN.md).  python3 research/intrinsic_target/intrinsic.py"""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
import export_gih_c3_28set as e  # noqa: E402

PAIRS = ["WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG"]
COLS = "WUBRG"
SEED, KAPPAS = 20260922, [1.0, 0.5]


def fits(c, p):
    return len(c) > 0 and all(x in p for x in c)


def deck_terms(pool, sets):
    pw = pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')
    wrc = pw.pivot(index='set', columns='pair', values='wr_c')[PAIRS]
    cp = pd.concat([pd.read_csv(ROOT / f'research/deck_pair/data/{s}_cardpair.csv.gz') for s in sets]).rename(columns={'card_name': 'name'})
    d = pool[['set', 'name']].merge(cp, on=['set', 'name'], how='left')
    assert len(d) == len(pool)
    sh = d[[f'{p}_games' for p in PAIRS]].fillna(0).values.astype(float)
    tot = sh.sum(1, keepdims=True)
    sh = sh / np.maximum(tot, 1)
    WR = wrc.loc[pool['set']].values / 100
    bA = (sh * WR).sum(1)
    colors = pool.apply(lambda r: ''.join(c for c in COLS if r[f'color_{c}'] == 1), axis=1)

    def share_b(c):
        if not c:
            return [1.0] * 10
        w = [1.0 if fits(c, p) else 0.0 for p in PAIRS]
        if sum(w) == 0:
            w = [1.0 if all(x in c for x in p) else 0.0 for p in PAIRS]
        return w
    shb = np.array([share_b(c) for c in colors])
    shb = shb / shb.sum(1, keepdims=True)
    bB = (shb * WR).sum(1)
    return bA, bB, (tot[:, 0] > 0)


def metrics(df, p, y):
    out = {'mae_pp': float(np.mean(np.abs(p - y)) * 100)}
    per = {}
    for s, idx in df.groupby('set').groups.items():
        i = df.index.get_indexer(idx)
        per[s] = {'mae_pp': float(np.mean(np.abs(p[i] - y[i])) * 100), 'spearman': float(spearmanr(p[i], y[i]).correlation)}
    out['spearman_mean'] = float(np.mean([v['spearman'] for v in per.values()]))
    return out, per


def main():
    pool, base, cols = e.training()
    nums = base + cols
    sets = sorted(pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')['set'].unique())
    pool = pool[pool['set'].isin(sets)].reset_index(drop=True)
    bA, bB, has = deck_terms(pool, sets)
    print('cards', len(pool), 'without pair data', int((~has).sum()), flush=True)
    pool['bA'], pool['bB'] = bA, bB
    y = pool['actual_gih'].values
    preds = {'A': np.zeros(len(pool))} | {f'B{k}': np.zeros(len(pool)) for k in KAPPAS}
    t0 = time.time()
    for s in sets:
        te = (pool['set'] == s).to_numpy()
        tr = pool[~te].copy()
        for name in preds:
            tgt = tr['actual_gih'] if name == 'A' else tr['actual_gih'] - float(name[1:]) * tr['bA']
            tr2 = tr.assign(actual_gih=tgt)
            c, t, x = e.parts(tr2, pool[te], nums, SEED)
            p = c + 1.25 * (.7 * t + .3 * x - c)
            preds[name][te] = p
        print(s, round(time.time() - t0), flush=True)
    res = {'n_sets': len(sets), 'seed': SEED}
    per_all = {}
    for name, p in preds.items():
        m, per = metrics(pool, p, y)
        res[name] = m
        per_all[name] = per
        ya = y - float(name[1:] if name != 'A' else 1.0) * pool['bA'].values
        res[name]['vs_adjusted_target'] = metrics(pool, p, y - pool['bA'].values)[0]
        if name != 'A':
            res[name]['plus_oracle_deck_term'] = metrics(pool, p + float(name[1:]) * pool['bB'].values, y)[0]
    res['A']['plus_oracle_deck_term_kappa1'] = metrics(pool, preds['A'] + pool['bB'].values, y)[0]
    res['B1.0']['sets_better_mae'] = int(sum(per_all['B1.0'][s]['mae_pp'] < per_all['A'][s]['mae_pp'] for s in sets))
    res['B0.5']['sets_better_mae'] = int(sum(per_all['B0.5'][s]['mae_pp'] < per_all['A'][s]['mae_pp'] for s in sets))
    r = res
    r['rule_i'] = {'mae': r['B1.0']['mae_pp'] < r['A']['mae_pp'], 'spearman': r['B1.0']['spearman_mean'] > r['A']['spearman_mean'],
                   'sets': r['B1.0']['sets_better_mae'] >= 14}
    r['rule_i']['pass'] = all(r['rule_i'].values())
    by = {}
    for ro, g in pool.groupby('rarity_ord'):
        i = g.index.values
        by[int(ro)] = {n: float(np.mean(np.abs(preds[n][i] - y[i])) * 100) for n in preds}
    r['mae_by_rarity'] = by
    r['per_set'] = {n: per_all[n] for n in ('A', 'B1.0')}
    json.dump(r, open(HERE / 'result.json', 'w'), indent=1)
    pool[['set', 'name', 'rarity_ord', 'actual_gih', 'bA', 'bB']].assign(**{f'pred_{k}': v for k, v in preds.items()}).round(5).to_csv(HERE / 'oof.csv.gz', index=False, compression='gzip')
    print(json.dumps({k: v for k, v in r.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    main()
