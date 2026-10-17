"""A2 arms and evaluation (Rule F16, see PLAN.md).  python3 a2_eval.py arm <B15r|B15a|shuf_B15r|shuf_B15a> | evaluate"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; C9DIR = ROOT / 'research/c9_power_questions'
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects')); sys.path.insert(0, str(C9DIR))
_sp = importlib.util.spec_from_file_location('c9mod', C9DIR / 'c9.py'); c9 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(c9)
c5, e = c9.c5, c9.e
COLS = ['a2_off', 'a2_on', 'a2_p', 'a2_ev']; FLAG = 'a2_flag'


def load_pool():
    pool, base, cols = c9.load_pool()
    f = pd.read_csv(HERE / 'a2_features.csv').rename(columns={'off': 'a2_off', 'on': 'a2_on', 'p': 'a2_p', 'ev': 'a2_ev'})[['key'] + COLS]
    f[FLAG] = 1
    pool = pool.merge(f, on='key', how='left'); pool[FLAG] = pool[FLAG].fillna(0)
    for c in COLS: pool[c] = pool[c].fillna(-1)
    return pool, base, cols


def run_arm(name):
    pool, base, cols = load_pool()
    if name.startswith('shuf_'):
        rng = np.random.default_rng(20261016); p = pool.copy()
        for s, idx in p[p[FLAG] == 1].groupby('set').groups.items():
            idx = np.array(idx); p.loc[idx, COLS] = pool.loc[rng.permutation(idx), COLS].to_numpy()
        pool = p
    b10 = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    if name.endswith('B15r'):
        t = pool[FLAG] == 1; pool.loc[t, 'c9_m_GRADE'] = pool.loc[t, 'a2_ev']; nums = b10
    else:
        nums = b10 + COLS + [FLAG]
    seeds = c5.SEEDS if name in ('B15r', 'B15a') else c5.SEEDS[:1]
    pred = np.full(len(pool), np.nan); ck = HERE / f'ckpt_{name}'; ck.mkdir(exist_ok=True)
    for s in sorted(pool['set'].unique()):
        te = (pool['set'] == s).to_numpy()
        if (ck / f'{s}.npy').exists(): pred[te] = np.load(ck / f'{s}.npy'); continue
        ps = []
        for sd in seeds:
            c, t_, x = e.parts(pool[~te], pool[te], nums, sd); ps.append(c + 1.25 * (.7 * t_ + .3 * x - c))
        pred[te] = np.mean(ps, axis=0); np.save(ck / f'{s}.npy', pred[te]); print(name, s, flush=True)
    pool[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=pred).to_csv(HERE / f'oof_{name}.csv.gz', index=False, compression='gzip')


def evaluate():
    arms = {n: pd.read_csv(HERE / f'oof_{n}.csv.gz') for n in ['B15r', 'B15a', 'shuf_B15r', 'shuf_B15a']}
    arms['B10'] = pd.read_csv(C9DIR / 'oof_B10.csv.gz')
    res, per = {}, {}
    for k, df in arms.items(): res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k != 'B10':
            res[k]['sets_lower'] = int(sum(per[k][s]['mae_pp'] < per['B10'][s]['mae_pp'] for s in per[k]))
            res[k]['gain_pp'] = res['B10']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    rule = {}
    for a in ('B15r', 'B15a'):
        b, sh = res[a], res['shuf_' + a]
        r = {'mae': b['pooled_mae_pp'] < res['B10']['pooled_mae_pp'], 'spearman': b['spearman_mean'] > res['B10']['spearman_mean'],
             'sets': b['sets_lower'] >= 15, 'gain': b['gain_pp'] > 0.01, 'control': sh['gain_pp'] < b['gain_pp'] / 2}
        r['pass'] = all(r.values()); rule[a] = r
    res['rule_f16'] = rule; res['overall'] = any(r['pass'] for r in rule.values())
    k = lambda d: d['set'] + '|' + d['name']
    m = arms['B10'].assign(k=k(arms['B10']))
    for a in ('B15r', 'B15a'): m = m.merge(arms[a].assign(k=k(arms[a]))[['k', 'pred']].rename(columns={'pred': a}), on='k')
    f = pd.read_csv(HERE / 'a2_features.csv').set_index('key'); t = m[m.k.isin(f.index)].copy()
    t['ev'] = t.k.map(f.ev)
    ae = lambda c: float((t[c] - t.actual_gih).abs().mean() * 100)
    res['selected'] = {'n': int(len(t)), 'mae': {c: ae(c) for c in ['pred', 'B15r', 'B15a']},
                       'spearman_ev_vs_actual_within_set': float(np.nanmean([g.ev.corr(g.actual_gih, method='spearman') for _, g in t.groupby('set')])),
                       'spearman_B10_vs_actual_within_set': float(np.nanmean([g.pred.corr(g.actual_gih, method='spearman') for _, g in t.groupby('set')]))}
    names = ['Avengers Assemble!', 'Rite of the Dragoncaller', 'Smile at Death', 'Agent Phil Coulson', 'Doubling Season', 'Arahbo, the First Fang', 'Necroduality', 'Chronicle of Victory']
    res['named'] = {n: {'actual': float(g.actual_gih.iloc[0] * 100), 'B10': float(g.pred.iloc[0] * 100), 'B15r': float(g.B15r.iloc[0] * 100), 'B15a': float(g.B15a.iloc[0] * 100), 'ev': float(g.ev.iloc[0])} for n in names for g in [t[t['name'] == n]] if len(g)}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1); print(json.dumps({a: b for a, b in res.items()}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    run_arm(sys.argv[2]) if sys.argv[1] == 'arm' else evaluate()
