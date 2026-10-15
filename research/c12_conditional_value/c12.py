"""C12 conditional value (Rule F13, see PLAN.md).

  python3 c12.py features | arm <B13|B13r|shuf_B13|shuf_B13r|onlyon> | evaluate
"""
import glob, importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import poisson

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C9DIR = ROOT / 'research/c9_power_questions'
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects'))
sys.path.insert(0, str(C9DIR))
_sp = importlib.util.spec_from_file_location('c9mod', C9DIR / 'c9.py'); c9 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(c9)
_sp = importlib.util.spec_from_file_location('check_raw_c12', HERE / 'check_raw.py'); cr = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(cr)
c5, e = c9.c5, c9.e
C12 = ['c12_k', 'c12_on', 'c12_off', 'c12_pon', 'c12_ev']
FLAG = 'c12_flag'
SEEDS = c5.SEEDS


def features():
    cards = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
    r1, e1 = cr.load_raw('s1', cards); r2, e2 = cr.load_raw('s2', cards)
    assert not e1 and not e2 and len(r1) == len(r2) == 1067
    c11 = pd.read_csv(ROOT / 'research/c11_set_reading_synergy/c11_features.csv').set_index('key')
    rows = []
    for r in cards[cards['target'] == 1].itertuples():
        if r.key not in c11.index:
            continue
        lam = c11.loc[r.key, 'c11_dwc'] + 0.5 * c11.loc[r.key, 'c11_iwc']
        lam_e = c11.loc[r.key, 'c11_exp']
        v = []
        for raw in (r1, r2):
            k, on, off = raw[(r.set, r.id)]
            pon = 1.0 if k == 0 else float(poisson.sf(k - 1, lam))
            pon_e = 1.0 if k == 0 else float(poisson.sf(k - 1, lam_e))
            v.append((k, on, off, pon, pon * on + (1 - pon) * off, pon_e * on + (1 - pon_e) * off))
        a = np.array(v, float); m = a.mean(0)
        rows.append({'key': r.key, 'c12_k': m[0], 'c12_on': m[1], 'c12_off': m[2], 'c12_pon': m[3], 'c12_ev': m[4], 'c12_ev_exp': m[5],
                     FLAG: 1, 'ev1': a[0, 4], 'ev2': a[1, 4], 'on1': a[0, 1], 'on2': a[1, 1]})
    f = pd.DataFrame(rows); f.to_csv(HERE / 'c12_features.csv', index=False)
    print(len(f)); print(f[C12 + ['c12_ev_exp']].describe().round(3).to_string())
    ag = {c: round(float(f[a].corr(f[b], method='spearman')), 3) for c, (a, b) in {'ev': ('ev1', 'ev2'), 'on': ('on1', 'on2')}.items()}
    json.dump(ag, open(HERE / 'agreement.json', 'w')); print('agreement', ag)


def load_pool(variant):
    pool, base, cols = c9.load_pool()
    f = pd.read_csv(HERE / 'c12_features.csv')[['key', FLAG] + C12]
    pool = pool.merge(f, on='key', how='left')
    pool[FLAG] = pool[FLAG].fillna(0)
    for c in C12:
        pool[c] = pool[c].fillna(-1)
    return pool, base, cols


def shuffled(pool):
    rng = np.random.default_rng(20261016)
    p = pool.copy()
    for s, idx in p[p[FLAG] == 1].groupby('set').groups.items():
        idx = np.array(idx); perm = rng.permutation(idx)
        p.loc[idx, C12] = pool.loc[perm, C12].to_numpy()
    return p


def run_arm(name):
    pool, base, cols = load_pool(name)
    if name.startswith('shuf_'):
        pool = shuffled(pool)
    b10 = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    if name.endswith('B13r'):
        t = pool[FLAG] == 1
        pool.loc[t, 'c9_m_GRADE'] = pool.loc[t, 'c12_ev']
        nums = b10
    elif name.endswith('B13'):
        nums = b10 + C12 + [FLAG]
    else:
        nums = b10 + ['c12_on', FLAG]
    seeds = SEEDS if name in ('B13', 'B13r') else SEEDS[:1]
    pred = np.full(len(pool), np.nan)
    ck = HERE / f'ckpt_{name}'; ck.mkdir(exist_ok=True)
    for s in sorted(pool['set'].unique()):
        te = (pool['set'] == s).to_numpy(); ps = []
        if (ck / f'{s}.npy').exists():
            pred[te] = np.load(ck / f'{s}.npy'); print(name, s, 'cached', flush=True); continue
        for sd in seeds:
            c, t_, x = e.parts(pool[~te], pool[te], nums, sd)
            ps.append(c + 1.25 * (.7 * t_ + .3 * x - c))
        pred[te] = np.mean(ps, axis=0); np.save(ck / f'{s}.npy', pred[te])
        print(name, s, flush=True)
    pool[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=pred).to_csv(HERE / f'oof_{name}.csv.gz', index=False, compression='gzip')
    json.dump({'n_features': len(nums), 'seeds': seeds}, open(HERE / f'meta_{name}.json', 'w'))


def evaluate():
    arms = {Path(f).name[4:-7]: pd.read_csv(f) for f in sorted(glob.glob(str(HERE / 'oof_*.csv.gz')))}
    arms['B10'] = pd.read_csv(C9DIR / 'oof_B10.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k != 'B10':
            res[k]['sets_lower_mae_vs_B10'] = int(sum(per[k][s]['mae_pp'] < per['B10'][s]['mae_pp'] for s in per[k]))
            res[k]['mae_gain_vs_B10_pp'] = res['B10']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    rule = {}
    for a in ('B13', 'B13r'):
        if a in arms:
            b, sh = res[a], res.get('shuf_' + a)
            r = {'mae': b['pooled_mae_pp'] < res['B10']['pooled_mae_pp'], 'spearman': b['spearman_mean'] > res['B10']['spearman_mean'],
                 'sets': b['sets_lower_mae_vs_B10'] >= 15, 'gain': b['mae_gain_vs_B10_pp'] > 0.01,
                 'control': (sh is not None) and sh['mae_gain_vs_B10_pp'] < b['mae_gain_vs_B10_pp'] / 2}
            r['pass'] = all(r.values()); rule[a] = r
    res['rule_f13'] = rule; res['rule_f13_overall'] = any(r['pass'] for r in rule.values())
    key = lambda d: d['set'] + '|' + d['name']
    m = arms['B10'].assign(k=key(arms['B10']))
    for a in ('B13', 'B13r'):
        if a in arms:
            m = m.merge(arms[a].assign(k=key(arms[a]))[['k', 'pred']].rename(columns={'pred': 'p_' + a}), on='k')
    f = pd.read_csv(HERE / 'c12_features.csv').set_index('key')
    c9f = pd.read_csv(C9DIR / 'c9_features.csv.gz').set_index('key')
    m['tg'] = m['k'].isin(f.index).astype(int); m['pon'] = m['k'].map(f['c12_pon']); m['ev'] = m['k'].map(f['c12_ev']); m['grade'] = m['k'].map(c9f['c9_m_GRADE'])
    m['arank'] = m.groupby('set').actual_gih.rank(ascending=False)
    pcols = ['pred'] + [c for c in m.columns if c.startswith('p_')]
    ae = lambda g: {'n': int(len(g)), **{c: float((g[c] - g['actual_gih']).abs().mean() * 100) for c in pcols}}
    res['by_target'] = {str(t): ae(g) for t, g in m.groupby('tg')}
    res['by_rarity_targets'] = {int(r): ae(g) for r, g in m[m.tg == 1].groupby('rarity_ord')}
    t = m[m.tg == 1].copy(); t['q'] = pd.qcut(t['pon'].rank(method='first'), 4, labels=False)
    res['by_pon_quartile'] = {int(q): ae(g) for q, g in t.groupby('q')}
    from sklearn.metrics import roc_auc_score
    y = (t.arank <= 15).astype(int)
    res['auc_top15_targets'] = {c: float(roc_auc_score(y, t[c])) for c in ['ev', 'grade'] + pcols}
    names = ['Avengers Assemble!', 'Chronicle of Victory', 'Necroduality', 'Rite of the Dragoncaller', 'Smile at Death', 'Oko, Lorwyn Liege']
    res['named'] = {n: {'actual_pct': float(g.actual_gih.iloc[0] * 100), **{c: float(g[c].iloc[0] * 100) for c in pcols}} for n in names for g in [m[m['name'] == n]] if len(g)}
    res['per_set'] = {s: {a: per[a][s] for a in ('B10', 'B13', 'B13r') if a in per} for s in per['B10']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
