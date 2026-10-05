"""C7c rarity-weighted set support vs C5 (Rule F7c, see PLAN.md).

  python3 c7c.py features [--fra <target.json.gz>]
  python3 c7c.py arm <B7c|B7c_counts|B7c_weighted|B7c_shuffled>
  python3 c7c.py evaluate
"""
import argparse, glob, gzip, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/c7_tag_synergy'))
import c7  # noqa: E402
c5, e, TAGS = c7.c5, c7.e, c7.TAGS

PAIRS = [(a, b, w) for a, b, w in c7.PAIRS if w == 2]
assert len(PAIRS) == 18
KEEP = ['W', 'Wlvl', 'sup_cnt_set', 'sup_cnt_col', 'sup_w_set', 'sup_w_col']
SYN = [f'g7c_{k}' for k in KEEP]
SYNS = [f'g7cs_{k}' for k in KEEP]
DRAFT = {0: 10.0, 1: 3.0, 2: 0.875, 3: 0.125}
PLAY = {0: 7.0, 1: 3.5, 2: 1.3, 3: 0.2}
FRA_DEFAULT = '/home/claude/limited-forecast-pages/data/target.json.gz'
RAR = {'common': 0, 'uncommon': 1, 'rare': 2, 'mythic': 3}


def rarity_map(fra_path):
    pool, base, cols = e.training()
    m = {f"{s}|{n}": int(r) for s, n, r in zip(pool['set'], pool['name'], pool['rarity_ord'])}
    for c in json.loads(gzip.open(fra_path, 'rt', encoding='utf-8').read())['cards']:
        if c['rarity'] in RAR:
            m[f"FRA|{c['id']}"] = RAR[c['rarity']]
    return m


def weights(keys, rar):
    """expected copies seen per 3 packs for every card key (0 if no rarity = basic land)."""
    sets = np.array([k.split('|')[0] for k in keys])
    r = np.array([rar.get(k, -1) for k in keys])
    w = np.zeros(len(keys))
    layout = {}
    for s in np.unique(sets):
        rs = r[sets == s]
        n = {q: int((rs == q).sum()) for q in range(4)}
        slots = PLAY if n[1] >= 95 else DRAFT
        layout[s] = 'play' if n[1] >= 95 else 'draft'
        for q in range(4):
            if n[q]:
                w[(sets == s) & (r == q)] = 3 * slots[q] / n[q]
    return w, layout


def build(S, P, L, sets, cols, auto, w):
    n = len(P)
    Sp = np.clip(S, 0, None)
    iu = np.triu_indices(len(TAGS), 1)
    ws = S[iu]; nz = ws != 0
    a_i, b_i, wt = iu[0][nz], iu[1][nz], ws[nz]
    both = P[:, a_i] * P[:, b_i]
    out = {'W': both @ wt, 'Wlvl': (np.minimum(L[:, a_i], L[:, b_i]) * (both > 0)) @ wt}
    for k in ('sup_cnt_set', 'sup_cnt_col', 'sup_w_set', 'sup_w_col'):
        out[k] = np.zeros(n)
    colset = [set(c) for c in cols]
    for s in np.unique(sets):
        ids = np.where((sets == s) & (auto == 0))[0]
        if len(ids) < 3:
            continue
        Ps, ws_ = P[ids], w[ids]
        tot_c, tot_w = Ps.sum(0), (Ps * ws_[:, None]).sum(0)
        for j, i in enumerate(ids):
            dc, dw = tot_c - Ps[j], tot_w - Ps[j] * ws_[j]
            m = np.array([(len(colset[i] & colset[k]) > 0 or not colset[i]) for k in ids]); m[j] = False
            cc = Ps[m].sum(0) if m.any() else dc
            cw = (Ps[m] * ws_[m][:, None]).sum(0) if m.any() else dw
            pa = P[i]
            out['sup_cnt_set'][i] = pa @ (Sp @ dc); out['sup_cnt_col'][i] = pa @ (Sp @ cc)
            out['sup_w_set'][i] = pa @ (Sp @ dw); out['sup_w_col'][i] = pa @ (Sp @ cw)
    return out


def features(fra_path):
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    f = pd.read_csv(ROOT / 'research/c5_atomic_effects/c5_features.csv.gz').set_index('key')
    info = {}
    for r in u.itertuples():
        for k in str(r.keys).split(';'):
            info[k] = (r.colors, r.auto)
    keys = list(f.index)
    rar = rarity_map(fra_path)
    L = f[[f'c5_{t}' for t in TAGS]].to_numpy(dtype=float)
    P = (L > 0).astype(float)
    sets = np.array([k.split('|')[0] for k in keys])
    cols = [info[k][0] for k in keys]
    auto = np.array([info[k][1] for k in keys])
    auto = np.where(np.array([k not in rar for k in keys]), 1, auto)   # no rarity = basic land
    w, layout = weights(keys, rar)
    real = build(c7.matrix(PAIRS), P, L, sets, cols, auto, w)
    perm = np.random.default_rng(20261004).permutation(len(TAGS))
    sh = build(c7.matrix([(TAGS[perm[c7.IDX[a]]], TAGS[perm[c7.IDX[b]]], x) for a, b, x in PAIRS]), P, L, sets, cols, auto, w)
    t = pd.DataFrame({'key': keys, **{f'g7c_{k}': real[k] for k in KEEP}, **{f'g7cs_{k}': sh[k] for k in KEEP}})
    t.loc[auto == 1, [c for c in t.columns if c != 'key']] = 0.0
    t.to_csv(HERE / 'c7c_features.csv.gz', index=False, compression='gzip')
    json.dump(layout, open(HERE / 'layouts.json', 'w'), indent=1, sort_keys=True)
    print(layout)
    print(t[SYN].describe().round(3).to_string())
    print('corr cnt vs w (set):', float(np.corrcoef(t.g7c_sup_cnt_set, t.g7c_sup_w_set)[0, 1]))


def load_pool():
    pool, base, cols, miss = c5.load_pool()
    g = pd.read_csv(HERE / 'c7c_features.csv.gz')
    pool = pool.merge(g, on='key', how='left')
    assert pool[SYN[0]].isna().mean() < 0.03
    pool[SYN + SYNS] = pool[SYN + SYNS].fillna(0)
    return pool, base, cols, miss


def arm_nums(name, base, cols):
    b5 = c5.arm_nums('B5', base, cols)
    return {'B7c': b5 + SYN, 'B7c_counts': b5 + SYN[:4], 'B7c_weighted': b5 + SYN[:2] + SYN[4:], 'B7c_shuffled': b5 + SYNS}[name]


def run_arm(name):
    pool, base, cols, miss = load_pool()
    nums = arm_nums(name, base, cols)
    seeds = c5.SEEDS if name == 'B7c' else c5.SEEDS[:1]
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
    arms['B7b'] = pd.read_csv(ROOT / 'research/c7b_strong_pairs/oof_B7b.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k in ('A', 'B5', 'B7b'):
            continue
        res[k]['sets_lower_mae_vs_B5'] = int(sum(per[k][s]['mae_pp'] < per['B5'][s]['mae_pp'] for s in per[k]))
        res[k]['mae_gain_vs_B5_pp'] = res['B5']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    if 'B7c' in arms:
        b5, b = res['B5'], res['B7c']
        r = {'mae': b['pooled_mae_pp'] < b5['pooled_mae_pp'], 'spearman': b['spearman_mean'] > b5['spearman_mean'],
             'sets': b['sets_lower_mae_vs_B5'] >= 15, 'gain': b5['pooled_mae_pp'] - b['pooled_mae_pp'] > 0.01}
        if 'B7c_shuffled' in arms:
            r['control_below_half'] = res['B7c_shuffled']['mae_gain_vs_B5_pp'] < 0.5 * b['mae_gain_vs_B5_pp']
        r['pass'] = all(r.values())
        res['rule_f7c'] = r
        res['per_set'] = {s: {'B5': per['B5'][s], 'B7c': per['B7c'][s]} for s in per['B7c']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd'); ap.add_argument('arm', nargs='?'); ap.add_argument('--fra', default=FRA_DEFAULT)
    a = ap.parse_args()
    {'features': lambda: features(a.fra), 'arm': lambda: run_arm(a.arm), 'evaluate': evaluate}[a.cmd]()
