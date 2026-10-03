"""C5 atomic effect tags vs C4 / production (Rule F5, see PLAN.md).

  python3 c5.py features
  python3 c5.py arm <B5|A_C5|tags_only|binarised>
  python3 c5.py evaluate
"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
sys.path.insert(0, str(HERE))
import check_raw as cr  # noqa: E402  (before export_gih_c3_28set)
import export_gih_c3_28set as e  # noqa: E402

C4DIR = ROOT / 'research/c4_fine_effects'
C4_NUM = [f'c4_{c}' for c in 'DMG TGT SPD SWG EVA TURN DEAD SCALE TEMPO VULN STACK SYNO DRAIN MANA'.split()]
C4_ROLE = [f'c4_role_{r}' for r in 'ADVFRTSNO']
GROUPS = {
    'removal': 'KD KX DM DA MS BN TP FT ED CS PA SW',
    'flow': 'DR SC RC TU IM TK CL',
    'growth': 'PC PT PP AN CP EQ',
    'combat': 'FL MN FS DT LL HS VG RH IN FH',
    'opponent': 'DS ST MI DL TX',
    'economy': 'RM FX CR SK CY',
    'trigger': 'ET AT DY UP SP LD SA CH KC RE',
    'risk': 'SE DW CD RN SD',
}
assert sorted(sum((v.split() for v in GROUPS.values()), [])) == sorted(cr.TAGS)
TAGC = [f'c5_{t}' for t in cr.TAGS]
SCALE = ['c5_RATE', 'c5_CLK', 'c5_BLK']
CNT = ['c5_ntags', 'c5_nlvl2', 'c5_ngroups']
SEEDS = e.SEEDS


def features():
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    raw, errs = cr.load_raw()
    assert not errs
    rows = []
    for r in u.itertuples():
        if r.auto == 1:
            sc, tg = [0, 0, 0], {}
        else:
            sc, tg = raw[r.id]
        d = {f'c5_{t}': tg.get(t, 0) for t in cr.TAGS}
        d.update(dict(zip(SCALE, sc)))
        d['c5_ntags'] = len(tg)
        d['c5_nlvl2'] = sum(1 for v in tg.values() if v == 2)
        d['c5_ngroups'] = sum(any(t in tg for t in g.split()) for g in GROUPS.values())
        for k in str(r.keys).split(';'):
            rows.append({'key': k, 'id': r.id, **d})
    t = pd.DataFrame(rows)
    assert not t['key'].duplicated().any()
    t.to_csv(HERE / 'c5_features.csv.gz', index=False, compression='gzip')
    print(len(t), t['key'].str.startswith('FRA|').sum())
    print(t[TAGC].gt(0).mean().sort_values().round(3).to_string())


def load_pool():
    pool, base, cols = e.training()
    c4 = pd.read_csv(C4DIR / 'c4_features.csv.gz')
    c5 = pd.read_csv(HERE / 'c5_features.csv.gz')
    pool['key'] = pool['set'] + '|' + pool['name']
    pool = pool.merge(c4.drop(columns='id'), on='key', how='left').merge(c5.drop(columns='id'), on='key', how='left')
    miss = float(pool[TAGC[0]].isna().mean())
    assert miss < 0.03, miss
    allc = C4_NUM + C4_ROLE + TAGC + SCALE + CNT
    pool[allc] = pool[allc].fillna(0)
    for t in cr.TAGS:
        pool[f'c5b_{t}'] = (pool[f'c5_{t}'] > 0).astype(float)
    return pool, base, cols, miss


def arm_nums(name, base, cols):
    c4 = C4_NUM + C4_ROLE
    return {'B5': base + cols + c4 + TAGC + SCALE + CNT,
            'A_C5': base + cols + TAGC + SCALE + CNT,
            'tags_only': base + cols + c4 + TAGC,
            'binarised': base + cols + c4 + [f'c5b_{t}' for t in cr.TAGS] + SCALE + CNT}[name]


def run_arm(name):
    pool, base, cols, miss = load_pool()
    nums = arm_nums(name, base, cols)
    seeds = SEEDS if name == 'B5' else SEEDS[:1]
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
    json.dump({'missing_c5': miss, 'n_features': len(nums), 'seeds': seeds}, open(HERE / f'meta_{name}.json', 'w'))


def metrics(df):
    per = {s: {'mae_pp': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
               'spearman': float(spearmanr(g['pred'], g['actual_gih']).correlation)} for s, g in df.groupby('set')}
    return {'pooled_mae_pp': float((df['pred'] - df['actual_gih']).abs().mean() * 100),
            'spearman_mean': float(np.mean([v['spearman'] for v in per.values()]))}, per


def evaluate():
    arms = {Path(f).name[4:-7]: pd.read_csv(f) for f in sorted(glob.glob(str(HERE / 'oof_*.csv.gz')))}
    arms['A'] = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    arms['B'] = pd.read_csv(C4DIR / 'oof_B.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = metrics(df)
    for k in arms:
        if k in ('A', 'B'):
            continue
        for ref in ('B', 'A'):
            res[k][f'sets_lower_mae_vs_{ref}'] = int(sum(per[k][s]['mae_pp'] < per[ref][s]['mae_pp'] for s in per[k]))
    if 'B5' in arms:
        a, b, b5 = res['A'], res['B'], res['B5']
        res['rule_f5'] = {'mae': b5['pooled_mae_pp'] < b['pooled_mae_pp'], 'spearman': b5['spearman_mean'] > b['spearman_mean'],
                          'sets': b5['sets_lower_mae_vs_B'] >= 15, 'gain': b['pooled_mae_pp'] - b5['pooled_mae_pp'] > 0.01}
        res['rule_f5']['pass'] = all(res['rule_f5'].values())
        # by rarity: align on set+name
        key = lambda d: d['set'] + '|' + d['name']
        m = arms['A'].assign(k=key(arms['A'])).merge(arms['B'].assign(k=key(arms['B']))[['k', 'pred']].rename(columns={'pred': 'pB'}), on='k')
        m = m.merge(arms['B5'].assign(k=key(arms['B5']))[['k', 'pred']].rename(columns={'pred': 'p5'}), on='k')
        res['by_rarity'] = {int(r): {'A': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
                                     'B': float((g['pB'] - g['actual_gih']).abs().mean() * 100),
                                     'B5': float((g['p5'] - g['actual_gih']).abs().mean() * 100)} for r, g in m.groupby('rarity_ord')}
        res['per_set'] = {s: {'A': per['A'][s], 'B': per['B'][s], 'B5': per['B5'][s]} for s in per['B5']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
