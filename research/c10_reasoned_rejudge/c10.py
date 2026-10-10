"""C10 reasoned re-judgement vs B10 (Rule F11, see PLAN.md).

  python3 c10.py features | arm <B11|shuffled|pctonly> | evaluate
"""
import glob, importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C9DIR = ROOT / 'research/c9_power_questions'
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects'))
sys.path.insert(0, str(C9DIR))
_sp = importlib.util.spec_from_file_location('c9mod', C9DIR / 'c9.py'); c9 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(c9)
_sp = importlib.util.spec_from_file_location('check_raw_c10', HERE / 'check_raw.py'); cr = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(cr)
c5, e = c9.c5, c9.e
C10 = ['c10_pct', 'c10_grade', 'c10_spec', 'c10_dpct']
FLAG = 'c10_flag'
SEEDS = c5.SEEDS


def features():
    t = pd.read_csv(HERE / 'targets.csv'); t = t[t['target'] == 1]
    r1, e1 = cr.load_raw('r1'); r2, e2 = cr.load_raw('r2')
    assert not e1 and not e2
    rows = []
    for r in t.itertuples():
        a, b = r1[r.id], r2[r.id]
        rows.append({'id': r.id, 'c10_pct': (a[0] + b[0]) / 2, 'c10_grade': (a[1] + b[1]) / 2, 'c10_spec': (a[2] + b[2]) / 2,
                     'c10_dpct': abs(a[0] - b[0]), FLAG: 1, 'cls': r.cls})
    f = pd.DataFrame(rows)
    f.to_csv(HERE / 'c10_features.csv', index=False)
    print(len(f)); print(f[C10].describe().round(2).to_string())
    print('agreement r1 vs r2 (Spearman):', {k: round(float(pd.Series([r1[i][j] for i in f.id]).corr(pd.Series([r2[i][j] for i in f.id]), method='spearman')), 3) for j, k in enumerate(['PCT', 'GRADE', 'SPEC'])})


def load_pool():
    pool, base, cols = c9.load_pool()
    f = pd.read_csv(HERE / 'c10_features.csv')
    ids = pd.read_csv(C9DIR / 'c9_features.csv.gz')[['key', 'id']]
    pool = pool.merge(ids, on='key', how='left').merge(f, on='id', how='left')
    pool[FLAG] = pool[FLAG].fillna(0)
    for c in C10:
        pool[c] = pool[c].fillna(-1)
    return pool, base, cols


def shuffled(pool):
    rng = np.random.default_rng(20261009)
    p = pool.copy()
    for (s, cl), idx in p[p[FLAG] == 1].groupby(['set', 'cls']).groups.items():
        idx = np.array(idx); perm = rng.permutation(idx)
        p.loc[idx, C10] = pool.loc[perm, C10].to_numpy()
    return p


def run_arm(name):
    pool, base, cols = load_pool()
    if name == 'shuffled':
        pool = shuffled(pool)
    b10 = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    nums = {'B11': b10 + C10 + [FLAG], 'shuffled': b10 + C10 + [FLAG], 'pctonly': b10 + ['c10_pct', FLAG]}[name]
    seeds = SEEDS if name == 'B11' else SEEDS[:1]
    pred = np.full(len(pool), np.nan)
    for s in sorted(pool['set'].unique()):
        te = (pool['set'] == s).to_numpy(); ps = []
        for sd in seeds:
            c, t, x = e.parts(pool[~te], pool[te], nums, sd)
            ps.append(c + 1.25 * (.7 * t + .3 * x - c))
        pred[te] = np.mean(ps, axis=0)
        print(name, s, flush=True)
    pool[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=pred).to_csv(HERE / f'oof_{name}.csv.gz', index=False, compression='gzip')
    json.dump({'n_features': len(nums), 'seeds': seeds}, open(HERE / f'meta_{name}.json', 'w'))


def evaluate():
    arms = {Path(f).name[4:-7]: pd.read_csv(f) for f in sorted(glob.glob(str(HERE / 'oof_*.csv.gz')))}
    arms['B10'] = pd.read_csv(C9DIR / 'oof_B10.csv.gz')
    arms['B5'] = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k not in ('B10', 'B5'):
            res[k]['sets_lower_mae_vs_B10'] = int(sum(per[k][s]['mae_pp'] < per['B10'][s]['mae_pp'] for s in per[k]))
            res[k]['mae_gain_vs_B10_pp'] = res['B10']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    if 'B11' in arms:
        b, sh = res['B11'], res.get('shuffled')
        res['rule_f11'] = {'mae': b['pooled_mae_pp'] < res['B10']['pooled_mae_pp'], 'spearman': b['spearman_mean'] > res['B10']['spearman_mean'],
                           'sets': b['sets_lower_mae_vs_B10'] >= 15, 'gain': b['mae_gain_vs_B10_pp'] > 0.01,
                           'control': (sh is not None) and sh['mae_gain_vs_B10_pp'] < b['mae_gain_vs_B10_pp'] / 2}
        res['rule_f11']['pass'] = all(res['rule_f11'].values())
        key = lambda d: d['set'] + '|' + d['name']
        m = arms['B10'].assign(k=key(arms['B10'])).merge(arms['B11'].assign(k=key(arms['B11']))[['k', 'pred']].rename(columns={'pred': 'p11'}), on='k')
        f = pd.read_csv(HERE / 'c10_features.csv')
        ids = pd.read_csv(C9DIR / 'c9_features.csv.gz')[['key', 'id', 'c9_s_GRADE']].set_index('key')
        m['id'] = m['k'].map(ids['id']); m['sd'] = m['k'].map(ids['c9_s_GRADE'])
        m['tg'] = m['id'].isin(set(f['id'])).astype(int)
        ae = lambda g, c: float((g[c] - g['actual_gih']).abs().mean() * 100)
        res['by_target'] = {str(t): {'n': int(len(g)), 'B10': ae(g, 'pred'), 'B11': ae(g, 'p11')} for t, g in m.groupby('tg')}
        res['by_rarity'] = {int(r): {'B10': ae(g, 'pred'), 'B11': ae(g, 'p11')} for r, g in m.groupby('rarity_ord')}
        m['dq'] = pd.qcut(m['sd'].rank(method='first'), 4, labels=False)
        res['by_c9_disagreement_quartile'] = {int(q): {'B10': ae(g, 'pred'), 'B11': ae(g, 'p11')} for q, g in m.groupby('dq')}
        res['per_set'] = {s: {'B10': per['B10'][s], 'B11': per['B11'][s]} for s in per['B11']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
