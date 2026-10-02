"""C4 finer card-effect features vs production (Rule F, see PLAN.md).

  python3 c4.py features
  python3 c4.py arm <A_s1|B|B_numbers|B_roles|C4_instead_of_C3>
  python3 c4.py evaluate
"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
sys.path.insert(0, str(HERE))
import check_raw as cr  # noqa: E402  (must come before export_gih_c3_28set, which prepends another check_raw to sys.path)
import export_gih_c3_28set as e  # noqa: E402

NUM = ['DMG', 'TGT', 'SPD', 'SWG', 'EVA', 'TURN', 'DEAD', 'SCALE', 'TEMPO', 'VULN', 'STACK', 'SYNO', 'DRAIN', 'MANA']
ROLES = list('ADVFRTSNO')
C4_NUM = [f'c4_{c}' for c in NUM]
C4_ROLE = [f'c4_role_{r}' for r in ROLES]
SEEDS = e.SEEDS


def features():
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    raw, errs = cr.load_raw()
    assert not errs
    rows = []
    for r in u.itertuples():
        if r.auto == 1:
            v, role = [0] * 14, 'O'
        else:
            v, role = raw[r.id]
        for k in str(r.keys).split(';'):
            d = {'key': k, 'id': r.id}
            d.update({f'c4_{n}': x for n, x in zip(NUM, v)})
            d.update({f'c4_role_{x}': float(role == x) for x in ROLES})
            rows.append(d)
    t = pd.DataFrame(rows)
    assert not t['key'].duplicated().any()
    t.to_csv(HERE / 'c4_features.csv.gz', index=False, compression='gzip')
    print(len(t), t['key'].str.startswith('FRA|').sum())


def load_pool():
    pool, base, cols = e.training()
    c4 = pd.read_csv(HERE / 'c4_features.csv.gz')
    pool['key'] = pool['set'] + '|' + pool['name']
    pool = pool.merge(c4.drop(columns='id'), on='key', how='left', validate='one_to_one' if False else 'many_to_one')
    miss = float(pool[C4_NUM[0]].isna().mean())
    assert miss < 0.03, miss
    pool[C4_NUM + C4_ROLE] = pool[C4_NUM + C4_ROLE].fillna(0)
    return pool, base, cols, miss


def run_arm(name):
    pool, base, cols, miss = load_pool()
    nums = {'A_s1': base + cols, 'B': base + cols + C4_NUM + C4_ROLE, 'B_numbers': base + cols + C4_NUM,
            'B_roles': base + cols + C4_ROLE, 'C4_instead_of_C3': base + C4_NUM + C4_ROLE}[name]
    seeds = SEEDS if name == 'B' else SEEDS[:1]
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
    json.dump({'missing_c4': miss, 'n_features': len(nums), 'seeds': seeds}, open(HERE / f'meta_{name}.json', 'w'))


def metrics(df):
    per = {s: {'mae_pp': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
               'spearman': float(spearmanr(g['pred'], g['actual_gih']).correlation)} for s, g in df.groupby('set')}
    return {'pooled_mae_pp': float((df['pred'] - df['actual_gih']).abs().mean() * 100),
            'spearman_mean': float(np.mean([v['spearman'] for v in per.values()]))}, per


def evaluate():
    arms = {Path(f).name[4:-7]: pd.read_csv(f) for f in sorted(glob.glob(str(HERE / 'oof_*.csv.gz')))}
    arms['A'] = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = metrics(df)
    for k in arms:
        if k not in ('A', 'A_s1'):
            ref = 'A' if k == 'B' else 'A_s1'
            res[k]['sets_lower_mae_vs_' + ref] = int(sum(per[k][s]['mae_pp'] < per[ref][s]['mae_pp'] for s in per[k]))
    if 'B' in arms:
        a, b = res['A'], res['B']
        res['by_rarity'] = {int(r): {'A': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
                                     'B': float((arms['B'].loc[g.index, 'pred'] - g['actual_gih']).abs().mean() * 100)}
                            for r, g in arms['A'].groupby('rarity_ord')} if len(arms['A']) == len(arms['B']) else {}
        res['rule_f'] = {'mae': b['pooled_mae_pp'] < a['pooled_mae_pp'], 'spearman': b['spearman_mean'] > a['spearman_mean'],
                         'sets': b['sets_lower_mae_vs_A'] >= 15, 'gain': a['pooled_mae_pp'] - b['pooled_mae_pp'] > 0.01}
        res['rule_f']['pass'] = all(res['rule_f'].values())
        res['per_set'] = {s: {'A': per['A'][s], 'B': per['B'][s]} for s in per['B']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
