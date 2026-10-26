#!/usr/bin/env python3
"""G1 v2, PLAN_v2.md section 14: effect of the new judgements on the B10 prediction error, leave-one-set-out, past 28 sets.

  python3 g1v2_pred_eval.py [--sets AFR,BLB,...] [--identity] [--boot 10000] [--out eval_v2/pred_eval]
      --identity   replace nothing (the 'new' arms equal the baseline): machinery check, all deltas must be 0
No FRA data is read. No new AI call. Baseline = B10 re-run, must equal c9_power_questions/oof_B10.csv.gz.
"""
import argparse, json, sys, warnings
from pathlib import Path
import numpy as np, pandas as pd

warnings.filterwarnings('ignore')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g1  # noqa: E402
import g1v2_eval as ev  # noqa: E402
c9, e, c5 = g1.c9, g1.e, g1.c5
F, MAX = ev.F, ev.MAX
SEED = 20261028
ARMS = ['B_rm', 'A_all', 'C_si', 'D_rmsi']


def answers():
    """per judged past unit: 3 passes x 7 answers, from raw_v2 (past-set batches)."""
    U = pd.read_csv(HERE / 'units.csv')
    U = U[U.set != 'FRA'].reset_index(drop=True)
    B = pd.read_csv(HERE / 'batches.csv')
    B = B[B.set != 'FRA']
    got = {p: {} for p in ev.PASSES}
    for p in ev.PASSES:
        for b in B[B['pass'] == p].itertuples():
            ids = ev.input_ids(p, b.batch)
            raw = ev.read_raw(HERE / 'raw_v2', p, b.batch)
            assert not (set(ids) - set(raw)), (p, b.batch)
            got[p].update({i: raw[i] for i in ids})
    arr = np.array([[got[p][n] for p in ev.PASSES] for n in U.n], float)
    return U, arr


def c9_row(m, sd):
    d = dict(zip(c9.MEAN, m)); d.update(zip(c9.SD, sd))
    d['c9_impuna'] = m[0] + m[1]; d['c9_valfloor'] = m[2] + m[3]; d['c9_bomb'] = m[6] - 1.25 * m[5]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sets'); ap.add_argument('--identity', action='store_true'); ap.add_argument('--no-conv', action='store_true', help='use the new answers without the old/new scale conversion (alpha=0, beta=1)')
    ap.add_argument('--boot', type=int, default=10000); ap.add_argument('--out', default=str(HERE / 'eval_v2' / 'pred_eval'))
    a = ap.parse_args()
    pool, base, cols, nums10, _ = g1.load_pool()
    pool = pool.reset_index(drop=True)
    assert pool.key.is_unique
    oof = pd.read_csv(HERE.parent / 'c9_power_questions' / 'oof_B10.csv.gz')
    assert (oof.set.values == pool.set.values).all() and (oof.name.values == pool.name.values).all()

    U, arr = answers()
    cp = pd.read_csv(HERE / 'eval_v2' / 'cards_past.csv').set_index('key')
    U['rarity_ord'] = U.key.map(cp.rarity_ord); U['setinfo'] = U.key.map(cp.setinfo).astype(bool)
    U['nonref_nosi'] = U.key.map(cp.nonref_nosi).astype(bool)
    for j, f in enumerate(F):
        U['new_' + f] = arr[:, :, j].mean(1); U['old_' + f] = U.key.map(cp['old_' + f])
    U['sd_new'] = list(arr.std(1))
    ridx = {k: i for i, k in enumerate(pool.key)}
    assert all(k in ridx for k in U.key)
    sets = a.sets.split(',') if a.sets else sorted(pool.set.unique())

    pred = {k: np.full(len(pool), np.nan) for k in ['base'] + ARMS}
    for s in sets:
        te = np.where(pool.set.values == s)[0]
        tr = pool[pool.set != s]
        Us = U[U.set == s]
        coef = ev.fit_conv(U[U.nonref_nosi & (U.set != s)])
        beta = np.array([coef[f][1] for f in F]); alpha = np.array([coef[f][0] for f in F])
        if a.no_conv:
            beta = np.ones(len(F)); alpha = np.zeros(len(F))
        rm = (Us.rarity_ord >= 2).to_numpy(); si = Us.setinfo.to_numpy()
        masks = {'B_rm': rm, 'A_all': np.ones(len(Us), bool), 'C_si': si, 'D_rmsi': rm & si}
        frames, owner = [pool.iloc[te]], [('base', te)]
        for arm in ARMS:
            sub = Us[masks[arm]]
            idx = np.array([ridx[k] for k in sub.key])
            fr = pool.iloc[idx].copy()
            if not a.identity:
                for r, (_, u) in enumerate(sub.iterrows()):
                    m = np.clip(alpha + beta * u[['new_' + f for f in F]].to_numpy(float), 0, MAX)
                    sd = beta * u.sd_new
                    for c, x in c9_row(m, sd).items():
                        fr.iloc[r, fr.columns.get_loc(c)] = x
            frames.append(fr); owner.append((arm, idx))
        test = pd.concat(frames, ignore_index=True)
        ps = []
        for sd_ in g1.SEEDS:
            c, t, x = e.parts(tr, test, nums10, sd_)
            ps.append(c + 1.25 * (.7 * t + .3 * x - c))
        p = np.mean(ps, axis=0)
        pos = 0
        for name, idx in owner:
            pred[name][idx] = p[pos:pos + len(idx)]
            pos += len(idx)
        print('done', s, flush=True)

    sel = pool.set.isin(sets).to_numpy()
    drift = float(np.abs(pred['base'][sel] - oof.pred.values[sel]).max() * 100)
    print('baseline vs oof_B10 max abs diff (pp):', drift)
    assert drift < 1e-6, drift
    # full-frame predictions per arm: baseline for cards that were not replaced
    full = {k: np.where(np.isnan(pred[k]), pred['base'], pred[k]) for k in ARMS}
    df = pool.loc[sel, ['set', 'name', 'key', 'rarity_ord', 'actual_gih']].copy()
    df['base'] = pred['base'][sel]
    for k in ARMS:
        df[k] = full[k][sel]; df['rep_' + k] = ~np.isnan(pred[k][sel])
    ui = U.set_index('key')
    df['group'] = df.key.map(ui.group) if 'group' in ui else df.key.map(cp.group)
    df['setinfo'] = df.key.map(ui.setinfo)
    df['year'] = df.set.map(ev.YEAR)
    df['rank_act'] = df.groupby('set').actual_gih.rank(ascending=False, method='first')

    def per_set_stats(arm):
        rows = {}
        scope = df['rep_' + arm]
        for s, g in df.groupby('set'):
            gs = g[g['rep_' + arm]]
            r = {}
            for lab, topn in (('all', None), ('t20', 20), ('t10', 10)):
                h = gs if topn is None else gs[gs.rank_act <= topn]
                r['n_' + lab] = len(h)
                r['ae_new_' + lab] = float((h[arm] - h.actual_gih).abs().sum() * 100); r['ae_base_' + lab] = float((h.base - h.actual_gih).abs().sum() * 100)
                r['un_new_' + lab] = float((h.actual_gih - h[arm]).sum() * 100); r['un_base_' + lab] = float((h.actual_gih - h.base).sum() * 100)
            r['sp_new'] = ev.spear(g[arm].to_numpy(), g.actual_gih.to_numpy()); r['sp_base'] = ev.spear(g.base.to_numpy(), g.actual_gih.to_numpy())
            rows[s] = r
        return pd.DataFrame(rows).T

    def summarize(S, idx=None):
        S = S if idx is None else S.iloc[idx]
        o = {}
        n = S.n_all.sum()
        o['n_cards'] = int(n)
        o['mae_base'] = float(S.ae_base_all.sum() / n) if n else None; o['mae_new'] = float(S.ae_new_all.sum() / n) if n else None
        o['d_mae'] = o['mae_new'] - o['mae_base'] if n else np.nan
        o['bias_d'] = float((S.un_new_all.sum() - S.un_base_all.sum()) / n) if n else np.nan
        for lab in ('t20', 't10'):
            m = S['n_' + lab].sum()
            o['n_' + lab] = int(m)
            o['d_under_' + lab] = float((S['un_new_' + lab].sum() - S['un_base_' + lab].sum()) / m) if m else np.nan
            o['under_base_' + lab] = float(S['un_base_' + lab].sum() / m) if m else np.nan
        o['d_spearman_sets'] = float((S.sp_new - S.sp_base).mean())
        return o

    rng = np.random.default_rng(SEED)
    res = {'sets': sets, 'identity': a.identity, 'baseline_vs_oof_max_pp': drift, 'arms': {}}
    ns = len(sets)
    bidx = rng.integers(0, ns, (a.boot, ns))
    for arm in ARMS:
        S = per_set_stats(arm)
        point = summarize(S)
        boots = [summarize(S, b) for b in bidx] if arm == 'B_rm' or True else []
        ci = {}
        for k in ('d_mae', 'd_under_t20', 'd_under_t10', 'd_spearman_sets', 'bias_d'):
            v = np.array([b[k] for b in boots], float)
            ci[k] = [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
        res['arms'][arm] = {**point, 'ci95': ci}
    # judged-only Spearman for the primary arm (R/M judged cards pooled within set, mean over sets)
    g = df[df.rep_B_rm]
    sp = [(ev.spear(h.B_rm.to_numpy(), h.actual_gih.to_numpy()), ev.spear(h.base.to_numpy(), h.actual_gih.to_numpy())) for _, h in g.groupby('set')]
    sp = np.array([x for x in sp if not np.isnan(x[0]) and not np.isnan(x[1])])
    res['arms']['B_rm']['spearman_judged_rm_only'] = {'new': float(sp[:, 0].mean()), 'base': float(sp[:, 1].mean()), 'diff': float((sp[:, 0] - sp[:, 1]).mean())}
    # B_rm splits (point estimates, not used for the verdict)
    sp_ = df[df.rep_B_rm].copy()
    sp_['ae_new'] = (sp_.B_rm - sp_.actual_gih).abs() * 100; sp_['ae_base'] = (sp_.base - sp_.actual_gih).abs() * 100
    sp_['err_new'] = (sp_.actual_gih - sp_.B_rm) * 100; sp_['err_base'] = (sp_.actual_gih - sp_.base) * 100
    splits = {}
    for name, key in (('group', 'group'), ('setinfo', 'setinfo'), ('era', None)):
        k = sp_[key] if key else np.where(sp_.year <= 2024, '2021-24', '2025+')
        for v, h in sp_.groupby(k):
            splits[f'{name}={v}'] = {'n': int(len(h)), 'mae_base': float(h.ae_base.mean()), 'mae_new': float(h.ae_new.mean()),
                                    'd_mae': float(h.ae_new.mean() - h.ae_base.mean()), 'bias_base': float(h.err_base.mean()), 'bias_new': float(h.err_new.mean())}
    res['B_rm_splits'] = splits
    r = res['arms']['B_rm']
    c = r['ci95']
    pt = r['d_mae'] < 0 and r['d_under_t20'] < 0 and r['d_under_t10'] <= 0 and r['d_spearman_sets'] >= 0
    res['verdict'] = {'point_estimates_all_met': bool(pt), 'd_mae_ci_upper_below_0': bool(c['d_mae'][1] < 0),
                      'M1': r['d_mae'] < 0, 'M2_top20': r['d_under_t20'] < 0, 'M2_top10': r['d_under_t10'] <= 0, 'M3': r['d_spearman_sets'] >= 0,
                      'label': ('支持' if pt and c['d_mae'][1] < 0 else '保留(弱い支持)' if pt else '不支持')}
    out = Path(a.out)
    out.parent.mkdir(exist_ok=True)
    Path(str(out) + '.json').write_text(json.dumps(res, indent=1, default=float))
    df.to_csv(str(out) + '_cards.csv.gz', index=False)
    print(json.dumps(res, indent=1, default=float))


if __name__ == '__main__':
    main()
