"""C11 set-list reading vs B10 (Rule F12, see PLAN.md).

  python3 c11.py features | arm <B12|shuffled|payonly> | evaluate
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
_sp = importlib.util.spec_from_file_location('check_raw_c11', HERE / 'check_raw.py'); cr = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(cr)
c5, e = c9.c5, c9.e
C11 = ['c11_pay', 'c11_exp', 'c11_dpay', 'c11_dw', 'c11_dwc', 'c11_iw', 'c11_iwc']
FLAG = 'c11_flag'
SEEDS = c5.SEEDS


def subtypes(t):
    return set(t.split('—', 1)[1].replace('/', ' ').split()) if '—' in t else set()


def features():
    cards = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
    cards['freq'] = cards['freq'].astype(float)
    r1, e1 = cr.load_raw('s1', cards); r2, e2 = cr.load_raw('s2', cards)
    assert not e1 and not e2
    rows = []
    for s, g in cards.groupby('set'):
        g = g.reset_index(drop=True)
        fq = dict(zip(g['id'], g['freq'])); col = dict(zip(g['id'], g['colors'].astype(str)))
        st = [(i, subtypes(t)) for i, t in zip(g['id'], g['type'])]
        for r in g[g['target'] == 1].itertuples():
            vals = []
            for raw in (r1, r2):
                pay, exp, D, I = raw[(s, r.id)]
                def w(lst):
                    ids = set()
                    for kind, v in lst:
                        if kind == 'id':
                            ids.add(v)
                        else:
                            ids |= {i for i, ss in st if v in ss}
                    ids.discard(r.id); ids &= set(fq)
                    allw = sum(fq[i] for i in ids)
                    mine = set(str(r.colors))
                    cw = sum(fq[i] for i in ids if (not mine) or (not col[i]) or (set(col[i]) & mine))
                    return allw, cw
                dw, dwc = w(D); iw, iwc = w(I)
                vals.append((pay, exp, dw, dwc, iw, iwc))
            v = np.array(vals, float)
            m = v.mean(0)
            rows.append({'key': r.key, 'c11_pay': m[0], 'c11_exp': m[1], 'c11_dpay': abs(v[0, 0] - v[1, 0]),
                         'c11_dw': m[2], 'c11_dwc': m[3], 'c11_iw': m[4], 'c11_iwc': m[5], FLAG: 1,
                         'pay1': v[0, 0], 'pay2': v[1, 0], 'dwc1': v[0, 3], 'dwc2': v[1, 3]})
    f = pd.DataFrame(rows)
    f.to_csv(HERE / 'c11_features.csv', index=False)
    print(len(f)); print(f[C11].describe().round(3).to_string())
    sp = lambda a, b: round(float(f[a].corr(f[b], method='spearman')), 3)
    ag = {'PAY': sp('pay1', 'pay2'), 'dwc': sp('dwc1', 'dwc2')}
    json.dump(ag, open(HERE / 'agreement.json', 'w')); print('agreement', ag)


def load_pool():
    pool, base, cols = c9.load_pool()
    f = pd.read_csv(HERE / 'c11_features.csv')[['key', FLAG] + C11]
    pool = pool.merge(f, on='key', how='left')
    pool[FLAG] = pool[FLAG].fillna(0)
    for c in C11:
        pool[c] = pool[c].fillna(-1)
    return pool, base, cols


def shuffled(pool):
    rng = np.random.default_rng(20261010)
    p = pool.copy()
    for s, idx in p[p[FLAG] == 1].groupby('set').groups.items():
        idx = np.array(idx); perm = rng.permutation(idx)
        p.loc[idx, C11] = pool.loc[perm, C11].to_numpy()
    return p


def run_arm(name):
    pool, base, cols = load_pool()
    if name == 'shuffled':
        pool = shuffled(pool)
    b10 = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    nums = {'B12': b10 + C11 + [FLAG], 'shuffled': b10 + C11 + [FLAG], 'payonly': b10 + ['c11_pay', FLAG]}[name]
    seeds = SEEDS if name == 'B12' else SEEDS[:1]
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
    if 'B12' in arms:
        b, sh = res['B12'], res.get('shuffled')
        res['rule_f12'] = {'mae': b['pooled_mae_pp'] < res['B10']['pooled_mae_pp'], 'spearman': b['spearman_mean'] > res['B10']['spearman_mean'],
                           'sets': b['sets_lower_mae_vs_B10'] >= 15, 'gain': b['mae_gain_vs_B10_pp'] > 0.01,
                           'control': (sh is not None) and sh['mae_gain_vs_B10_pp'] < b['mae_gain_vs_B10_pp'] / 2}
        res['rule_f12']['pass'] = all(res['rule_f12'].values())
        key = lambda d: d['set'] + '|' + d['name']
        m = arms['B10'].assign(k=key(arms['B10'])).merge(arms['B12'].assign(k=key(arms['B12']))[['k', 'pred']].rename(columns={'pred': 'p12'}), on='k')
        f = pd.read_csv(HERE / 'c11_features.csv').set_index('key')
        m['tg'] = m['k'].isin(f.index).astype(int); m['dwc'] = m['k'].map(f['c11_dwc'])
        ae = lambda g: {'n': int(len(g)), 'B10': float((g['pred'] - g['actual_gih']).abs().mean() * 100), 'B12': float((g['p12'] - g['actual_gih']).abs().mean() * 100)}
        res['by_target'] = {str(t): ae(g) for t, g in m.groupby('tg')}
        res['by_rarity'] = {int(r): ae(g) for r, g in m.groupby('rarity_ord')}
        res['by_rarity_targets'] = {int(r): ae(g) for r, g in m[m.tg == 1].groupby('rarity_ord')}
        t = m[m.tg == 1].copy(); t['q'] = pd.qcut(t['dwc'].rank(method='first'), 4, labels=False)
        res['by_dwc_quartile'] = {int(q): ae(g) for q, g in t.groupby('q')}
        res['named'] = {n: ae(m[m['name'].str.contains(n, regex=False)]) for n in ['Avengers Assemble!', 'Chronicle of Victory', 'Necroduality'] if m['name'].str.contains(n, regex=False).any()}
        res['per_set'] = {s: {'B10': per['B10'][s], 'B12': per['B12'][s]} for s in per['B12']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
