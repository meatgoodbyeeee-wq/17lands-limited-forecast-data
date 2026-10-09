"""C9 power questions x 3 passes vs B5 (Rule F10, see PLAN.md).

  python3 c9.py features | agreement | arm <B10|p1only|meansonly|A_means> | evaluate
"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects'))
import c5  # noqa: E402
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location('check_raw_c9', HERE / 'check_raw.py')
cr9 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(cr9)
e = c5.e
F = ['IMP', 'UNA', 'VAL', 'FLOOR', 'FLEX', 'PLAY', 'GRADE']
MID = [2, 2, 2, 2, 1.5, 2, 5]
MEAN = [f'c9_m_{f}' for f in F]
SD = [f'c9_s_{f}' for f in F]
SUM = ['c9_impuna', 'c9_valfloor', 'c9_bomb']
P1 = [f'c9_p1_{f}' for f in F]
SEEDS = c5.SEEDS


def features():
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    raws = [cr9.load_raw(p) for p in cr9.PASSES]
    assert all(not er for _, er in raws)
    rows = []
    for r in u.itertuples():
        if r.auto == 1:
            m, s, p1 = list(MID), [0.0] * 7, list(MID)
        else:
            v = np.array([raws[i][0][r.id] for i in range(3)], float)
            m, s, p1 = v.mean(0).tolist(), v.std(0).tolist(), v[0].tolist()
        d = dict(zip(MEAN, m)); d.update(dict(zip(SD, s))); d.update(dict(zip(P1, p1)))
        d['c9_impuna'] = m[0] + m[1]; d['c9_valfloor'] = m[2] + m[3]; d['c9_bomb'] = m[6] - 1.25 * m[5]
        for k in str(r.keys).split(';'):
            rows.append({'key': k, 'id': r.id, **d})
    t = pd.DataFrame(rows)
    assert not t['key'].duplicated().any()
    t.to_csv(HERE / 'c9_features.csv.gz', index=False, compression='gzip')
    print(len(t))


def agreement():
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    ids = sorted(u.loc[u['auto'] == 0, 'id'])
    raws = [cr9.load_raw(p)[0] for p in cr9.PASSES]
    out = {}
    for j, f in enumerate(F):
        a = [np.array([r[i][j] for i in ids]) for r in raws]
        pr = [spearmanr(a[x], a[y]).correlation for x, y in [(0, 1), (0, 2), (1, 2)]]
        exact = np.mean([(a[x] == a[y]).mean() for x, y in [(0, 1), (0, 2), (1, 2)]])
        out[f] = {'spearman_pairs': [round(float(p), 3) for p in pr], 'exact_agree': round(float(exact), 3),
                  'mean_sd': round(float(np.mean(np.std(np.array(a), axis=0))), 3)}
    json.dump(out, open(HERE / 'agreement.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))


def load_pool():
    pool, base, cols, miss = c5.load_pool()
    c9 = pd.read_csv(HERE / 'c9_features.csv.gz')
    pool = pool.merge(c9.drop(columns='id'), on='key', how='left')
    allc = MEAN + SD + SUM + P1
    assert pool[MEAN[0]].isna().mean() < 0.03
    for c, v in zip(allc, MID * 1 + [0] * 7 + [0, 0, 0] + MID):
        pool[c] = pool[c].fillna(v)
    return pool, base, cols


def run_arm(name):
    pool, base, cols = load_pool()
    b5 = c5.arm_nums('B5', base, cols)
    nums = {'B10': b5 + MEAN + SD + SUM, 'p1only': b5 + P1, 'meansonly': b5 + MEAN,
            'A_means': base + cols + MEAN}[name]
    seeds = SEEDS if name == 'B10' else SEEDS[:1]
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
    arms['B5'] = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')
    arms['A'] = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k not in ('A', 'B5'):
            res[k]['sets_lower_mae_vs_B5'] = int(sum(per[k][s]['mae_pp'] < per['B5'][s]['mae_pp'] for s in per[k]))
            res[k]['mae_gain_vs_B5_pp'] = res['B5']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    if 'B10' in arms:
        b, b5 = res['B10'], res['B5']
        res['rule_f10'] = {'mae': b['pooled_mae_pp'] < b5['pooled_mae_pp'], 'spearman': b['spearman_mean'] > b5['spearman_mean'],
                           'sets': b['sets_lower_mae_vs_B5'] >= 15, 'gain': b['mae_gain_vs_B5_pp'] > 0.01}
        res['rule_f10']['pass'] = all(res['rule_f10'].values())
        key = lambda d: d['set'] + '|' + d['name']
        m = arms['B5'].assign(k=key(arms['B5'])).merge(arms['B10'].assign(k=key(arms['B10']))[['k', 'pred']].rename(columns={'pred': 'p10'}), on='k')
        res['by_rarity'] = {int(r): {'B5': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
                                     'B10': float((g['p10'] - g['actual_gih']).abs().mean() * 100)} for r, g in m.groupby('rarity_ord')}
        c5f = pd.read_csv(ROOT / 'research/c5_atomic_effects/c5_features.csv.gz')[['key', 'c5_ntags']].set_index('key')['c5_ntags']
        m['nt'] = m['k'].map(c5f).fillna(0)
        m['bin'] = pd.cut(m['nt'], [-1, 1, 3, 5, 99], labels=['0-1', '2-3', '4-5', '6+'])
        res['by_ntags'] = {str(r): {'n': int(len(g)), 'B5': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
                                    'B10': float((g['p10'] - g['actual_gih']).abs().mean() * 100)} for r, g in m.groupby('bin', observed=True)}
        res['per_set'] = {s: {'B5': per['B5'][s], 'B10': per['B10'][s]} for s in per['B10']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'agreement': agreement, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
