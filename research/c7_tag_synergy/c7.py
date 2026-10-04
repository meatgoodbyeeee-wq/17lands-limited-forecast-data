"""C7 tag synergy features vs C5 (Rule F7, see PLAN.md).

  python3 c7.py features
  python3 c7.py arm <B7|B7_within|B7_context|B7_shuffled>
  python3 c7.py evaluate
  python3 c7.py describe
"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects'))
import c5  # noqa: E402
e = c5.e
TAGS = c5.cr.TAGS

# tag tag weight  (symmetric). Written from Magic knowledge before any scoring.
SYNERGY = """
DT FS 2
DT MN 2
DT FL 1
DT IN 1
DT FT 2
DT FH 1
FS PT 1
FS PC 1
FS MN 1
FS EQ 1
LL FL 2
LL MN 2
LL FS 1
LL PC 1
LL PT 1
LL DT 1
LL DL 1
LL VG 1
LL EQ 1
LL SD 1
FL PC 1
FL PT 1
FL EQ 2
FL AN 1
FL AT 1
FL VG 1
FL HS 1
MN EQ 1
MN PC 1
MN PT 1
MN AT 1
HS PT 1
HS AT 1
HS EQ 1
VG AT 1
VG PC 1
VG EQ 1
IN EQ 1
IN PC 1
FH CS 1
FH PT 1
FH ET 1
TP AT 1
TP MN 1
BN ET 2
BN CP 1
FT PC 2
FT PT 1
FT IN 1
SW IN 2
SW RC 1
SW TK -1
SW AN -1
SW PC -1
CS DR 1
DR SC 1
DR SP 1
DR CL 1
RC SA 2
RC DY 1
RC RE 2
RC ET 1
DY SA 2
DY TK 1
DY CP 1
ET CP 2
ET SA 1
TK AN 2
TK SA 2
TK PC 1
TK PT 1
TK EQ 1
TK PP 1
TK CP 1
CL SA 1
CL SK 1
CL RM 1
IM SP 1
UP SK 1
UP SA 1
PC PP 1
PC CP 1
PC AN 1
PC ET 1
AN CP 1
DS DL 1
DL SD 1
DL SA 1
ST SA 2
RM SK 2
RM KC 1
CR SP 1
CR SK 1
CY RC 1
CY SC 1
CY DR 1
AT PC 1
AT PT 1
SP PT 1
SP CP 1
LD FX 2
LD RM 1
LD TU 1
RE SA 1
CS HS -1
CS AT -1
RH HS -1
SE TK -1
"""
PAIRS = [(a, b, int(w)) for a, b, w in (l.split() for l in SYNERGY.strip().splitlines())]
assert all(a in TAGS and b in TAGS and a != b for a, b, _ in PAIRS)
assert len({tuple(sorted((a, b))) for a, b, _ in PAIRS}) == len(PAIRS) == 108, len(PAIRS)
IDX = {t: i for i, t in enumerate(TAGS)}
WITHIN = ['W', 'Wpos', 'Wneg', 'Wlvl']
CONTEXT = ['sup_set', 'fric_set', 'sup_col', 'fric_col']
SYN = [f'g7_{c}' for c in WITHIN + CONTEXT]
SYNS = [f'g7s_{c}' for c in WITHIN + CONTEXT]


def matrix(pairs):
    S = np.zeros((len(TAGS), len(TAGS)))
    for a, b, w in pairs:
        S[IDX[a], IDX[b]] = S[IDX[b], IDX[a]] = w
    return S


def build(S, P, L, sets, cols, auto):
    """P, L: n x 58 (presence, level); returns dict of 8 arrays."""
    n = len(P)
    Sp, Sn = np.clip(S, 0, None), np.clip(-S, 0, None)
    out = {}
    iu = np.triu_indices(len(TAGS), 1)
    ws = S[iu]
    nz = ws != 0
    a_i, b_i, w = iu[0][nz], iu[1][nz], ws[nz]
    both = P[:, a_i] * P[:, b_i]
    out['W'] = both @ w
    out['Wpos'] = both @ np.clip(w, 0, None)
    out['Wneg'] = both @ np.clip(-w, 0, None)
    out['Wlvl'] = (np.minimum(L[:, a_i], L[:, b_i]) * (both > 0)) @ w
    for k in ('sup_set', 'fric_set', 'sup_col', 'fric_col'):
        out[k] = np.zeros(n)
    colset = [set(c) for c in cols]
    for s in np.unique(sets):
        ids = np.where((sets == s) & (auto == 0))[0]
        if len(ids) < 3:
            continue
        Ps = P[ids]
        tot = Ps.sum(0)
        for j, i in enumerate(ids):
            d = (tot - Ps[j]) / (len(ids) - 1)
            m = np.array([(len(colset[i] & colset[k]) > 0 or not colset[i]) for k in ids]); m[j] = False
            dc = Ps[m].mean(0) if m.any() else d
            pa = P[i]
            out['sup_set'][i] = pa @ (Sp @ d); out['fric_set'][i] = pa @ (Sn @ d)
            out['sup_col'][i] = pa @ (Sp @ dc); out['fric_col'][i] = pa @ (Sn @ dc)
    return out


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
    real = build(matrix(PAIRS), P, L, sets, cols, auto)
    rng = np.random.default_rng(20261004)
    perm = rng.permutation(len(TAGS))
    shuf = build(matrix([(TAGS[perm[IDX[a]]], TAGS[perm[IDX[b]]], w) for a, b, w in PAIRS]), P, L, sets, cols, auto)
    t = pd.DataFrame({'key': keys, **{f'g7_{k}': v for k, v in real.items()}, **{f'g7s_{k}': v for k, v in shuf.items()}})
    t.loc[auto == 1, [c for c in t.columns if c != 'key']] = 0.0
    t.to_csv(HERE / 'c7_features.csv.gz', index=False, compression='gzip')
    print(t[SYN].describe().round(3).to_string())
    print('corr real vs c5_ntags', {c: round(float(np.corrcoef(t[c], f['c5_ntags'])[0, 1]), 2) for c in SYN})
    print('perm seed 20261004 first 5', [(TAGS[i], TAGS[perm[i]]) for i in range(5)])


def load_pool():
    pool, base, cols, miss = c5.load_pool()
    g = pd.read_csv(HERE / 'c7_features.csv.gz')
    pool = pool.merge(g, on='key', how='left')
    assert pool[SYN[0]].isna().mean() < 0.03
    pool[SYN + SYNS] = pool[SYN + SYNS].fillna(0)
    return pool, base, cols, miss


def arm_nums(name, base, cols):
    b5 = c5.arm_nums('B5', base, cols)
    return {'B7': b5 + SYN, 'B7_within': b5 + SYN[:4], 'B7_context': b5 + SYN[4:], 'B7_shuffled': b5 + SYNS}[name]


def run_arm(name):
    pool, base, cols, miss = load_pool()
    nums = arm_nums(name, base, cols)
    seeds = c5.SEEDS if name == 'B7' else c5.SEEDS[:1]
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
    arms['B'] = pd.read_csv(ROOT / 'research/c4_fine_effects/oof_B.csv.gz')
    arms['B5'] = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k in ('A', 'B', 'B5'):
            continue
        res[k]['sets_lower_mae_vs_B5'] = int(sum(per[k][s]['mae_pp'] < per['B5'][s]['mae_pp'] for s in per[k]))
        res[k]['mae_gain_vs_B5_pp'] = res['B5']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    if 'B7' in arms:
        b5, b7 = res['B5'], res['B7']
        r = {'mae': b7['pooled_mae_pp'] < b5['pooled_mae_pp'], 'spearman': b7['spearman_mean'] > b5['spearman_mean'],
             'sets': b7['sets_lower_mae_vs_B5'] >= 15, 'gain': b5['pooled_mae_pp'] - b7['pooled_mae_pp'] > 0.01}
        r['pass'] = all(r.values())
        if 'B7_shuffled' in arms:
            r['control_below_half'] = res['B7_shuffled']['mae_gain_vs_B5_pp'] < 0.5 * res['B7']['mae_gain_vs_B5_pp']
        res['rule_f7'] = r
        key = lambda d: d['set'] + '|' + d['name']
        m = arms['B5'].assign(k=key(arms['B5'])).merge(arms['B7'].assign(k=key(arms['B7']))[['k', 'pred']].rename(columns={'pred': 'p7'}), on='k')
        res['by_rarity'] = {int(q): {'B5': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
                                     'B7': float((g['p7'] - g['actual_gih']).abs().mean() * 100)} for q, g in m.groupby('rarity_ord')}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps(res, indent=1))


def describe():
    o = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')
    o['key'] = o['set'] + '|' + o['name']
    o['res'] = (o['actual_gih'] - o['pred']) * 100
    f = pd.read_csv(ROOT / 'research/c5_atomic_effects/c5_features.csv.gz').drop(columns='id')
    d = o.merge(f, on='key', how='left').dropna(subset=[f'c5_{TAGS[0]}'])
    P = (d[[f'c5_{t}' for t in TAGS]].to_numpy() > 0)
    r = d['res'].to_numpy()
    r0 = float(r.mean())
    r = r - r0   # centred on the overall mean residual
    sd = float(r.std())
    S = matrix(PAIRS)
    rows = []
    for i in range(len(TAGS)):
        for j in range(i + 1, len(TAGS)):
            m = P[:, i] & P[:, j]
            if m.sum() >= 1:
                rows.append({'a': TAGS[i], 'b': TAGS[j], 'n': int(m.sum()), 'weight': int(S[i, j]),
                             'mean_res_pp': float(r[m].mean()), 'z': float(r[m].mean() / (sd / np.sqrt(m.sum())))})
    t_all = pd.DataFrame(rows)
    t = t_all[t_all.n >= 30]
    sm = {}
    for name, g in (('positive', t[t.weight > 0]), ('negative', t[t.weight < 0]), ('unlisted', t[t.weight == 0])):
        sm[name] = {'pairs': int(len(g)), 'mean_res_pp_weighted': float(np.average(g['mean_res_pp'], weights=g['n'])) if len(g) else None,
                    'share_pairs_res_gt0': float((g['mean_res_pp'] > 0).mean()) if len(g) else None}
    NAMED = {frozenset(p) for p in [('DT', 'FS'), ('DT', 'MN'), ('LL', 'FL'), ('LL', 'MN'), ('FL', 'EQ'), ('TK', 'AN'), ('RM', 'SK'), ('RC', 'SA'), ('SW', 'TK'), ('SW', 'PC'), ('CS', 'HS')]}
    named = t_all[t_all.apply(lambda x: frozenset((x.a, x.b)) in NAMED, axis=1)]
    out = {'overall_mean_residual_pp': r0, 'residual_sd_pp': sd, 'n_cards': int(len(d)), 'summary': sm, 'named': named.to_dict('records'),
           'top5_positive_listed': t[t.weight > 0].nlargest(5, 'z').to_dict('records'), 'top5_negative_listed': t[t.weight < 0].nsmallest(5, 'z').to_dict('records')}
    t_all.to_csv(HERE / 'pair_residuals.csv', index=False)
    json.dump(out, open(HERE / 'describe.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate, 'describe': describe}[sys.argv[1]]()
