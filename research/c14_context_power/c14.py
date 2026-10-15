"""C14: C9 power questions answered with the whole set in view (Rule F15, see PLAN.md).

  python3 c14.py features | agreement | arm | evaluate
"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C9DIR = ROOT / 'research/c9_power_questions'
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects'))
sys.path.insert(0, str(C9DIR))
_sp = importlib.util.spec_from_file_location('c9mod', C9DIR / 'c9.py'); c9 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(c9)
_sp = importlib.util.spec_from_file_location('check_raw_c14', HERE / 'check_raw.py'); cr = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(cr)
c5, e = c9.c5, c9.e
SEEDS = c5.SEEDS
REPL = c9.MEAN + c9.SD + c9.SUM
NAMED = ['Avengers Assemble!', 'Chronicle of Victory', 'Necroduality', 'Rite of the Dragoncaller', 'Smile at Death', 'Oko, Lorwyn Liege']


def features():
    cards = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
    r1, e1 = cr.load_raw('s1', cards); r2, e2 = cr.load_raw('s2', cards)
    assert not e1 and not e2 and len(r1) == len(r2) == len(cards)
    rows = []
    for r in cards.itertuples():
        v = np.array([r1[(r.set, r.id)], r2[(r.set, r.id)]], float)
        m, s = v.mean(0), v.std(0)
        d = dict(zip(c9.MEAN, m)); d.update(dict(zip(c9.SD, s)))
        d['c9_impuna'] = m[0] + m[1]; d['c9_valfloor'] = m[2] + m[3]; d['c9_bomb'] = m[6] - 1.25 * m[5]
        d['key'] = r.key; rows.append(d)
    f = pd.DataFrame(rows); f.to_csv(HERE / 'c14_features.csv.gz', index=False, compression='gzip'); print(len(f))
    old = pd.read_csv(C9DIR / 'c9_features.csv.gz').set_index('key')
    j = f.set_index('key').join(old[c9.MEAN], rsuffix='_old', how='inner')
    print('corr with original C9 (Spearman) per question:', {k: round(float(j[k].corr(j[k + '_old'], method='spearman')), 3) for k in c9.MEAN})
    ag = {k: round(float(pd.Series([r1[x][i] for x in r1]).corr(pd.Series([r2[x][i] for x in r1]), method='spearman')), 3) for i, k in enumerate(c9.F)}
    json.dump(ag, open(HERE / 'agreement.json', 'w')); print('pass agreement', ag)


def load_pool():
    pool, base, cols = c9.load_pool()
    f = pd.read_csv(HERE / 'c14_features.csv.gz').set_index('key')
    auto = set()
    u = pd.read_csv(C9DIR / 'cards.csv.gz', keep_default_na=False)
    for r in u[u['auto'] == 1].itertuples():
        auto |= set(str(r.keys).split(';'))
    hit = pool['key'].isin(f.index) & ~pool['key'].isin(auto)
    for c in REPL:
        pool.loc[hit, c] = pool.loc[hit, 'key'].map(f[c])
    print('replaced', int(hit.sum()), 'of', len(pool))
    return pool, base, cols


def run_arm():
    pool, base, cols = load_pool()
    nums = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    pred = np.full(len(pool), np.nan)
    ck = HERE / 'ckpt_B14'; ck.mkdir(exist_ok=True)
    for s in sorted(pool['set'].unique()):
        te = (pool['set'] == s).to_numpy()
        if (ck / f'{s}.npy').exists():
            pred[te] = np.load(ck / f'{s}.npy'); print(s, 'cached', flush=True); continue
        ps = []
        for sd in SEEDS:
            c, t, x = e.parts(pool[~te], pool[te], nums, sd)
            ps.append(c + 1.25 * (.7 * t + .3 * x - c))
        pred[te] = np.mean(ps, axis=0); np.save(ck / f'{s}.npy', pred[te]); print(s, flush=True)
    pool[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=pred).to_csv(HERE / 'oof_B14.csv.gz', index=False, compression='gzip')


def evaluate():
    b14 = pd.read_csv(HERE / 'oof_B14.csv.gz'); b10 = pd.read_csv(C9DIR / 'oof_B10.csv.gz')
    r14, p14 = c5.metrics(b14); r10, p10 = c5.metrics(b10)
    res = {'B10': r10, 'B14': r14}
    res['B14']['sets_lower_mae_vs_B10'] = int(sum(p14[s]['mae_pp'] < p10[s]['mae_pp'] for s in p14))
    res['B14']['mae_gain_vs_B10_pp'] = r10['pooled_mae_pp'] - r14['pooled_mae_pp']
    res['rule_f15'] = {'mae': r14['pooled_mae_pp'] < r10['pooled_mae_pp'], 'spearman': r14['spearman_mean'] > r10['spearman_mean'],
                       'sets': res['B14']['sets_lower_mae_vs_B10'] >= 15, 'gain': res['B14']['mae_gain_vs_B10_pp'] > 0.01}
    res['rule_f15']['pass'] = all(res['rule_f15'].values())
    k = lambda d: d['set'] + '|' + d['name']
    m = b10.assign(k=k(b10)).merge(b14.assign(k=k(b14))[['k', 'pred']].rename(columns={'pred': 'p14'}), on='k')
    m['y'] = m.actual_gih * 100; m['p10'] = m.pred * 100; m['p14'] = m.p14 * 100
    ae = lambda g: {'n': int(len(g)), 'B10': float((g.p10 - g.y).abs().mean()), 'B14': float((g.p14 - g.y).abs().mean())}
    res['by_rarity'] = {int(r): ae(g) for r, g in m.groupby('rarity_ord')}
    res['underpred_gt5_by_B10'] = ae(m[m.y - m.p10 > 5]); res['overpred_gt5_by_B10'] = ae(m[m.p10 - m.y > 5])
    f11 = pd.read_csv(ROOT / 'research/c11_set_reading_synergy/c11_features.csv')
    m['c11t'] = m['k'].isin(set(f11['key'])).astype(int)
    res['c11_targets'] = {str(t): ae(g) for t, g in m.groupby('c11t')}
    from sklearn.metrics import roc_auc_score
    m['rk'] = m.groupby('set')['y'].rank(ascending=False); yy = (m.rk <= 10).astype(int)
    res['auc_top10'] = {'B10': float(roc_auc_score(yy, m.p10)), 'B14': float(roc_auc_score(yy, m.p14))}
    top = m[m.rk <= 10]
    res['top10_mean_dev'] = {'actual': float((top.y - m.groupby(['set', 'rarity_ord']).y.transform('mean')[top.index]).mean()),
                             'B10': float((top.p10 - m.groupby(['set', 'rarity_ord']).p10.transform('mean')[top.index]).mean()),
                             'B14': float((top.p14 - m.groupby(['set', 'rarity_ord']).p14.transform('mean')[top.index]).mean())}
    m['p14rk'] = m.groupby('set')['p14'].rank(ascending=False); m['p10rk'] = m.groupby('set')['p10'].rank(ascending=False)
    res['named'] = {n: {'actual': float(g.y.iloc[0]), 'B10': float(g.p10.iloc[0]), 'B14': float(g.p14.iloc[0]), 'actual_rank': float(g.rk.iloc[0]),
                        'B10_rank': float(g.p10rk.iloc[0]), 'B14_rank': float(g.p14rk.iloc[0])} for n in NAMED for g in [m[m['name'] == n]] if len(g)}
    res['per_set'] = {s: {'B10': p10[s], 'B14': p14[s]} for s in p14}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({a: b for a, b in res.items() if a != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': run_arm, 'evaluate': evaluate}[sys.argv[1]]()
