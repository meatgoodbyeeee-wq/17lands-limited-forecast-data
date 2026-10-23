#!/usr/bin/env python3
"""G1 plan v2, past-set evaluation (PLAN_v2.md 7.1, 7.2, 7.4 P1-P4, 7.5 year split, 12.1 interpretations).

  python3 g1v2_eval.py [--raw-dir raw_v2] [--out-dir eval_v2] [--boot 10000]
  python3 g1v2_eval.py --selftest      # synthetic raw answers (old C9 means + noise) in a temp dir; checks the code path only

Reads only past-set data (28 sets). FRA units are ignored here. Writes eval_v2/: past_result.json, past_gate.json, conversion_all28.json, cards_past.csv.
Run once on the complete, validated raw_v2 of the past-set batches (3 passes). Nothing is refitted after seeing the result.
"""
import argparse, json, re, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g1_inputs as g1  # noqa: E402  (FIELDS, MAX, LINE)

C9 = HERE.parent / 'c9_power_questions'
F, MAX = g1.FIELDS, g1.MAX
PASSES = ['p1', 'p2', 'p3']
SEED = 20261028
YEAR = {**{s: 2021 for s in 'AFR KHM MID STX VOW'.split()}, **{s: 2022 for s in 'BRO DMU NEO SNC'.split()},
        **{s: 2023 for s in 'LCI LTR MOM ONE WOE'.split()}, **{s: 2024 for s in 'BLB DSK FDN MKM OTJ'.split()},
        **{s: 2025 for s in 'DFT EOE TDM TLA'.split()}, **{s: 2026 for s in 'ECL HOB MSH SOS TMT'.split()}}
TOL_P3, HOT, BASE_PP = -0.02, 0.5, 0.05


# ---------------------------------------------------------------- data
def input_ids(p, batch):
    t = (HERE / 'input_v2' / p / f'{batch}.txt').read_text()
    blocks = re.split(r'\n(?=#\d+ \|)', t)
    out = {}
    for b in blocks:
        m = re.match(r'#(\d+) \|', b)
        if m:
            out[int(m.group(1))] = 'SET INFO' in b
    return out


def read_raw(raw_dir, p, batch):
    f = raw_dir / p / f'{batch}.txt'
    if not f.exists():
        raise SystemExit(f'missing {f}')
    out = {}
    for n, line in enumerate(f.read_text().splitlines(), 1):
        if not line.strip():
            continue
        m = g1.LINE.match(line.strip())
        if not m:
            raise SystemExit(f'{f}:{n} bad format: {line!r} (run g1v2.py check first)')
        v = [int(x) for x in m.group(2).split()]
        if any(x < 0 or x > mx for x, mx in zip(v, MAX)):
            raise SystemExit(f'{f}:{n} out of range')
        out[int(m.group(1))] = v
    return out


def make_selftest_raw(d, U, old, seed=1):
    rng = np.random.default_rng(seed)
    B = pd.read_csv(HERE / 'batches.csv')
    for b in B[B.set != 'FRA'].itertuples():
        (d / b._1).mkdir(parents=True, exist_ok=True)
        lines = []
        for i in input_ids(b._1, b.batch):
            o = old.loc[U.set_index('n').loc[i, 'key']].to_numpy(float)
            v = np.clip(np.rint(o + rng.normal(0, 0.7, 7) + 0.1), 0, MAX).astype(int)
            lines.append(f'{i} ' + ' '.join(map(str, v)))
        (d / b._1 / f'{b.batch}.txt').write_text('\n'.join(lines) + '\n')


def load(raw_dir, selftest=False):
    U = pd.read_csv(HERE / 'units.csv')
    U = U[U.set != 'FRA'].reset_index(drop=True)
    pool = pd.read_csv(HERE / 'past_pool.csv.gz')
    cards = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    auto = {k for r in cards.itertuples() if r.auto == 1 for k in r.keys.split(';')}
    c9f = pd.read_csv(C9 / 'c9_features.csv.gz').set_index('key')
    old = c9f[[f'c9_m_{f}' for f in F]]
    old.columns = F
    base = pool[~pool.key.isin(auto) & ~pool.type_line.str.startswith('Basic') & pool.actual_gih.notna()]
    smean = base.groupby('set').actual_gih.mean()
    P = pool.set_index('key')
    U['actual'] = U.key.map(P.actual_gih)
    U['act_rel'] = (U.actual - U.set.map(smean)) * 100            # pp
    U['stratum'] = np.where(U.rarity_ord >= 2, 'RM', 'CU')
    U['year'] = U.set.map(YEAR)
    U['era'] = np.where(U.year <= 2024, '2021-24', '2025+')
    B = pd.read_csv(HERE / 'batches.csv')
    B = B[B.set != 'FRA']
    flag, got = {}, {p: {} for p in PASSES}
    for p in PASSES:
        for b in B[B['pass'] == p].itertuples():
            ids = input_ids(p, b.batch)
            raw = read_raw(raw_dir, p, b.batch)
            miss = set(ids) - set(raw)
            if miss:
                raise SystemExit(f'{p}/{b.batch}: missing ids {sorted(miss)[:5]}')
            for i in ids:
                got[p][i] = raw[i]
                if p == 'p1':
                    flag[i] = ids[i]
    if selftest:
        pass
    arr = np.array([[got[p][n] for p in PASSES] for n in U.n], float)   # unit x pass x 7
    for j, f in enumerate(F):
        U['new_' + f] = arr[:, :, j].mean(1)
        U['old_' + f] = old.loc[U.key, f].to_numpy()
    U['setinfo'] = U.n.map(flag).astype(bool)
    U['nonref_nosi'] = (U.group == 'other') & ~U.setinfo
    return U


def selftest_prepare():
    U = pd.read_csv(HERE / 'units.csv')
    c9f = pd.read_csv(C9 / 'c9_features.csv.gz').set_index('key')
    old = c9f[[f'c9_m_{f}' for f in F]]
    old.columns = F
    d = Path(tempfile.mkdtemp(prefix='g1v2_selftest_'))
    make_selftest_raw(d, U, old)
    return d


# ---------------------------------------------------------------- metrics
def spear(x, y):
    if len(x) < 3:
        return np.nan
    a, b = rankdata(x), rankdata(y)
    a, b = a - a.mean(), b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den else np.nan


def loso_dev(U, col):
    """deviation act_rel - (a + b*grade) with the line fitted on the other 27 sets, per stratum."""
    dev = np.full(len(U), np.nan)
    for st in ('RM', 'CU'):
        S = U.stratum == st
        for s in U.set.unique():
            tr = S & (U.set != s)
            te = S & (U.set == s)
            if te.sum() == 0:
                continue
            b, a = np.polyfit(U.loc[tr, col], U.loc[tr, 'act_rel'], 1)
            dev[te.to_numpy()] = U.loc[te, 'act_rel'] - (a + b * U.loc[te, col])
    return dev


def fit_conv(T):
    """old = alpha + beta*new for each of the 7 questions on rows T (non-reference random cards without SET INFO)."""
    return {f: tuple(float(x) for x in np.polyfit(T['new_' + f], T['old_' + f], 1)[::-1]) for f in F}   # (alpha, beta)


def apply_conv(D, coef):
    out = {}
    for j, f in enumerate(F):
        a, b = coef[f]
        out[f] = np.clip(a + b * D['new_' + f].to_numpy(), 0, MAX[j])
    return out


def subsets(U):
    return {'all': np.ones(len(U), bool), 'type_ref': (U.group == 'type_ref').to_numpy(), 'random300': (U.group == 'other').to_numpy(),
            'setinfo': U.setinfo.to_numpy(), 'no_setinfo': (~U.setinfo).to_numpy()}


def stratum_masks(U):
    return {'RM': (U.stratum == 'RM').to_numpy(), 'CU': (U.stratum == 'CU').to_numpy(), 'both': np.ones(len(U), bool)}


def cell_stats(U, idx, mask_s, mask_g, dev_o, dev_n):
    sel = idx[mask_s[idx] & mask_g[idx]]
    if len(sel) < 5:
        return None
    ar = U.act_rel.to_numpy()[sel]
    so, sn = spear(U.old_GRADE.to_numpy()[sel], ar), spear(U.new_GRADE.to_numpy()[sel], ar)
    do, dn = np.nanmean(np.abs(dev_o[sel])), np.nanmean(np.abs(dev_n[sel]))
    return dict(n=int(len(sel)), sp_old=so, sp_new=sn, d_sp=sn - so, dev_old=float(do), dev_new=float(dn), d_dev=float(dn - do))


def evaluate(U, boot, rng):
    dev_o, dev_n = loso_dev(U, 'old_GRADE'), loso_dev(U, 'new_GRADE')
    # ---- conversion (LOSO) and converted GRADE
    conv_grade = np.full(len(U), np.nan)
    conv7 = {f: np.full(len(U), np.nan) for f in F}
    for s in U.set.unique():
        coef = fit_conv(U[U.nonref_nosi & (U.set != s)])
        te = (U.set == s).to_numpy()
        a = apply_conv(U[te], coef)
        for f in F:
            conv7[f][te] = a[f]
    for f in F:
        U['conv_' + f] = conv7[f]
    coef_all = fit_conv(U[U.nonref_nosi])
    base_pp = None
    cell = {}
    S, G = stratum_masks(U), subsets(U)
    allidx = np.arange(len(U))
    for sk, sm in S.items():
        for gk, gm in G.items():
            r = cell_stats(U, allidx, sm, gm, dev_o, dev_n)
            if r:
                cell[f'{sk}|{gk}'] = r
    # ---- bootstrap over sets
    by_set = {s: np.where(U.set.to_numpy() == s)[0] for s in U.set.unique()}
    names = list(by_set)
    reps = {k: {'d_sp': [], 'd_dev': []} for k in cell}
    for _ in range(boot):
        pick = rng.integers(0, len(names), len(names))
        idx = np.concatenate([by_set[names[i]] for i in pick])
        for k in cell:
            sk, gk = k.split('|')
            r = cell_stats(U, idx, S[sk], G[gk], dev_o, dev_n)
            if r:
                reps[k]['d_sp'].append(r['d_sp']); reps[k]['d_dev'].append(r['d_dev'])
    for k, r in cell.items():
        for m in ('d_sp', 'd_dev'):
            v = np.array(reps[k][m], float)
            v = v[~np.isnan(v)]
            r[m + '_ci'] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if len(v) else [np.nan, np.nan]
    # ---- P4: converted GRADE up by >= 0.5 -> share with act_rel <= 0
    U['grade_move'] = U.conv_GRADE - U.old_GRADE
    below = U.act_rel <= 0
    base = float(below.mean())
    hot = U.grade_move >= HOT
    p4 = {'base_rate': base, 'threshold': base + BASE_PP}
    for gk, m in (('all', np.ones(len(U), bool)), ('type_ref', (U.group == 'type_ref').to_numpy()), ('random300', (U.group == 'other').to_numpy())):
        h = hot.to_numpy() & m
        p4[gk] = {'n_cards': int(m.sum()), 'n_moved_up': int(h.sum()), 'share_below_avg': float(below[h].mean()) if h.sum() else None,
                  'fail': bool(h.sum() and below[h].mean() > base + BASE_PP)}
    # ---- criteria
    c = cell
    P1 = bool(c['RM|type_ref']['d_sp'] > 0 and c['RM|type_ref']['d_sp_ci'][0] > 0 and c['CU|type_ref']['d_sp'] >= 0)
    P2 = bool(c['RM|all']['d_dev'] < 0 and c['CU|all']['d_dev'] < 0 and c['RM|all']['d_dev_ci'][1] < 0)
    P3 = bool(c['both|random300']['d_sp'] >= TOL_P3)
    P4 = not (p4['all']['fail'] or p4['type_ref']['fail'])
    gate = {'P1': P1, 'P2': P2, 'P3': P3, 'P4': P4, 'all_pass': bool(P1 and P2 and P3 and P4),
            'note': 'P1: R/M type_ref Spearman diff>0 with set-bootstrap CI lower>0, and C/U diff>=0. P2: mean|dev| smaller for R/M and C/U, R/M CI upper<0. '
                    'P3: random 300 pooled Spearman diff >= -0.02. P4: share of converted-GRADE-up cards (>=+0.5) below average <= base+5pp (all 937 and type_ref 637).'}
    # ---- 7.5 year split (descriptive)
    era = {}
    for e in ('2021-24', '2025+'):
        m = (U.era == e).to_numpy()
        era[e] = {k: cell_stats(U, allidx, S[k.split('|')[0]], G[k.split('|')[1]] & m, dev_o, dev_n) for k in ('RM|all', 'CU|all', 'both|all', 'both|type_ref')}
        era[e]['mean_grade_move_conv'] = float(U.grade_move[m].mean())
    year = {}
    for y in sorted(U.year.unique()):
        m = (U.year == y).to_numpy()
        year[int(y)] = cell_stats(U, allidx, S['both'], m, dev_o, dev_n)
    # ---- level shift old vs new (raw and converted)
    shift = {f: {'old_mean': float(U['old_' + f].mean()), 'new_mean': float(U['new_' + f].mean()), 'conv_mean': float(U['conv_' + f].mean()),
                 'old_sd': float(U['old_' + f].std()), 'new_sd': float(U['new_' + f].std())} for f in F}
    U['dev_old'], U['dev_new'] = dev_o, dev_n
    res = {'n_cards': int(len(U)), 'boot': boot, 'seed': SEED, 'cells': cell, 'P4': p4, 'gate': gate, 'era_split': era, 'year_split': year,
           'level_shift': shift, 'conversion_loso_note': 'per-set LOSO coefficients are applied inside; the all-28 fit below is for FRA',
           'conversion_all28': {f: {'alpha': a, 'beta': b} for f, (a, b) in coef_all.items()},
           'conversion_fit_n': int(U.nonref_nosi.sum())}
    return res, coef_all, U


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', default=str(HERE / 'raw_v2')); ap.add_argument('--out-dir', default=str(HERE / 'eval_v2'))
    ap.add_argument('--boot', type=int, default=10000); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    raw = Path(a.raw_dir)
    out = Path(a.out_dir)
    if a.selftest:
        raw = selftest_prepare()
        out = Path(tempfile.mkdtemp(prefix='g1v2_selftest_out_'))
        a.boot = min(a.boot, 300)
        print('SELFTEST: synthetic answers in', raw, '- results mean nothing')
    out.mkdir(parents=True, exist_ok=True)
    U = load(raw, a.selftest)
    res, coef, U = evaluate(U, a.boot, np.random.default_rng(SEED))
    if a.selftest:
        res['SELFTEST'] = True
    (out / 'past_result.json').write_text(json.dumps(res, indent=1, default=float))
    (out / 'past_gate.json').write_text(json.dumps({**res['gate'], 'selftest': bool(a.selftest)}, indent=1))
    (out / 'conversion_all28.json').write_text(json.dumps(res['conversion_all28'], indent=1))
    U.drop(columns=['actual']).to_csv(out / 'cards_past.csv', index=False)
    g = res['gate']
    print(json.dumps({k: res['cells'][k] for k in ('RM|type_ref', 'CU|type_ref', 'both|random300', 'RM|all', 'CU|all')}, indent=1, default=float))
    print('P4', json.dumps(res['P4'], indent=1))
    print('GATE', {k: g[k] for k in ('P1', 'P2', 'P3', 'P4', 'all_pass')}, '-> outputs in', out)


if __name__ == '__main__':
    main()
