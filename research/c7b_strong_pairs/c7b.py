"""C7b strong synergy pairs only vs C5 (Rule F7b, see PLAN.md).

  python3 c7b.py features
  python3 c7b.py arm <B7b|B7b_within|B7b_context|B7b_shuffled>
  python3 c7b.py evaluate
"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/c7_tag_synergy'))
import c7  # noqa: E402  (also puts c5 / production on sys.path)
c5, e, TAGS = c7.c5, c7.e, c7.TAGS

PAIRS = [(a, b, w) for a, b, w in c7.PAIRS if w == 2]
assert len(PAIRS) == 18
KEEP = ['W', 'Wlvl', 'sup_set', 'sup_col']
SYN = [f'g7b_{k}' for k in KEEP]
SYNS = [f'g7bs_{k}' for k in KEEP]


def features():
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    f = pd.read_csv(ROOT / 'research/c5_atomic_effects/c5_features.csv.gz').set_index('key')
    info = {}
    for r in u.itertuples():
        for k in str(r.keys).split(';'):
            info[k] = (r.colors, r.auto)
    keys = list(f.index)
    L = f[[f'c5_{t}' for t in TAGS]].to_numpy(dtype=float)
    P = (L > 0).astype(float)
    sets = np.array([k.split('|')[0] for k in keys])
    cols = [info[k][0] for k in keys]
    auto = np.array([info[k][1] for k in keys])
    real = c7.build(c7.matrix(PAIRS), P, L, sets, cols, auto)
    perm = np.random.default_rng(20261004).permutation(len(TAGS))
    sh = c7.build(c7.matrix([(TAGS[perm[c7.IDX[a]]], TAGS[perm[c7.IDX[b]]], w) for a, b, w in PAIRS]), P, L, sets, cols, auto)
    t = pd.DataFrame({'key': keys, **{f'g7b_{k}': real[k] for k in KEEP}, **{f'g7bs_{k}': sh[k] for k in KEEP}})
    t.loc[auto == 1, [c for c in t.columns if c != 'key']] = 0.0
    assert float(np.abs(real['Wneg']).max()) == 0 and float(np.abs(real['fric_set']).max()) == 0
    assert np.allclose(real['W'], real['Wpos'])
    t.to_csv(HERE / 'c7b_features.csv.gz', index=False, compression='gzip')
    print(t[SYN + SYNS].describe().round(3).to_string())
    print('share of cards with W>0', float((t.g7b_W > 0).mean()), 'shuffled', float((t.g7bs_W > 0).mean()))


def load_pool():
    pool, base, cols, miss = c5.load_pool()
    g = pd.read_csv(HERE / 'c7b_features.csv.gz')
    pool = pool.merge(g, on='key', how='left')
    assert pool[SYN[0]].isna().mean() < 0.03
    pool[SYN + SYNS] = pool[SYN + SYNS].fillna(0)
    return pool, base, cols, miss


def arm_nums(name, base, cols):
    b5 = c5.arm_nums('B5', base, cols)
    return {'B7b': b5 + SYN, 'B7b_within': b5 + SYN[:2], 'B7b_context': b5 + SYN[2:], 'B7b_shuffled': b5 + SYNS}[name]


def run_arm(name):
    pool, base, cols, miss = load_pool()
    nums = arm_nums(name, base, cols)
    seeds = c5.SEEDS if name == 'B7b' else c5.SEEDS[:1]
    pred = np.full(len(pool), np.nan)
    for s in sorted(pool['set'].unique()):
        te = (pool['set'] == s).to_numpy()
        ps = []
        for sd in seeds:
            c, t, x = e.parts(pool[~te], pool[te], nums, sd)
            ps.append(c + 1.25 * (.7 * t + .3 * x - c))
        pred[te] = np.mean(ps, axis=0)
        print(name, s, flush=True)
    pool[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=pred).to_csv(HERE / f'oof_{name}.csv.gz', index=False, compression='gzip')
    json.dump({'n_features': len(nums), 'seeds': seeds}, open(HERE / f'meta_{name}.json', 'w'))


def evaluate():
    arms = {Path(f).name[4:-7]: pd.read_csv(f) for f in sorted(glob.glob(str(HERE / 'oof_*.csv.gz')))}
    arms['A'] = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    arms['B5'] = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')
    arms['B7'] = pd.read_csv(ROOT / 'research/c7_tag_synergy/oof_B7.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k in ('A', 'B5', 'B7'):
            continue
        res[k]['sets_lower_mae_vs_B5'] = int(sum(per[k][s]['mae_pp'] < per['B5'][s]['mae_pp'] for s in per[k]))
        res[k]['mae_gain_vs_B5_pp'] = res['B5']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    if 'B7b' in arms:
        b5, b = res['B5'], res['B7b']
        r = {'mae': b['pooled_mae_pp'] < b5['pooled_mae_pp'], 'spearman': b['spearman_mean'] > b5['spearman_mean'],
             'sets': b['sets_lower_mae_vs_B5'] >= 15, 'gain': b5['pooled_mae_pp'] - b['pooled_mae_pp'] > 0.01}
        if 'B7b_shuffled' in arms:
            r['control_below_half'] = res['B7b_shuffled']['mae_gain_vs_B5_pp'] < 0.5 * b['mae_gain_vs_B5_pp']
        r['pass'] = all(r.values())
        res['rule_f7b'] = r
        res['per_set'] = {s: {'B5': per['B5'][s], 'B7b': per['B7b'][s]} for s in per['B7b']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
