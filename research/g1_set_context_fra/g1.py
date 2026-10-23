"""G1 plan 2: set-context density features added to B10, leave-one-set-out on the 28 production sets (PLAN.md sections 4-5).

  python3 g1.py arm <B10SC|shuf|B10re>   # OOF predictions -> oof_<arm>.csv.gz   (B10re = B10 re-run in this environment, sanity check)
  python3 g1.py evaluate                 # Rule G1-LOSO, E1 top-card metrics -> result.json
  python3 g1.py freeze_fra --fra <target.json.gz>   # (plan 2 and plan 0 FRA predictions; only after PLAN.md is committed)

Reuses research/c9_power_questions (B10 definition), research/c5_atomic_effects (metrics), E1 metric definitions (Rule F18).
No FRA outcome data is read anywhere in this file.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/c9_power_questions'))
import c9  # noqa: E402
c5, e = c9.c5, c9.e

SC = ['sc_n_sup', 'sc_sup_share_max', 'sc_sup_share_min', 'sc_sup_E_max', 'sc_sup_E_min', 'sc_tribe_share', 'sc_chosen_share', 'sc_kw_share',
      'sc_ctyp_share', 'sc_ncsub_share', 'sc_sup_mk_n', 'sc_n_tgt', 'sc_tgt_share_max']
SEEDS = c5.SEEDS


def load_pool():
    pool, base, cols = c9.load_pool()
    f = pd.read_csv(HERE / 'sc_features.csv.gz').drop(columns=['id', 'set'])
    pool = pool.merge(f, on='key', how='left')
    miss = float(pool[SC[0]].isna().mean())
    pool[SC] = pool[SC].fillna(0.0)
    nums = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    return pool, base, cols, nums, miss


def run_arm(name):
    pool, base, cols, nums10, miss = load_pool()
    if name == 'shuf':
        rng = np.random.default_rng(20261023)
        for s in pool['set'].unique():
            idx = np.where(pool['set'] == s)[0]
            perm = rng.permutation(idx)
            pool.loc[pool.index[idx], SC] = pool.loc[pool.index[perm], SC].to_numpy()
    nums = nums10 if name == 'B10re' else nums10 + SC
    seeds = SEEDS if name in ('B10SC', 'B10re') else SEEDS[:1]
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
    json.dump({'n_features': len(nums), 'seeds': seeds, 'missing_sc_share': miss}, open(HERE / f'meta_{name}.json', 'w'))


def e1_per_set(df):
    """E1 (Rule F18) per-set top-10 metrics, same definitions as research/e1_top_card_metric/e1.py."""
    out = {}
    for s, g in df.groupby('set'):
        g = g.reset_index(drop=True)
        d = (g.pred - g.actual_gih) * 100
        top = g.actual_gih.rank(ascending=False, method='first') <= 10
        bot = g.actual_gih.rank(method='first') <= 10
        pr = g.pred.rank(ascending=False, method='first')
        out[s] = {'t_bias': d[top].mean(), 't_mae': d[top].abs().mean(), 'hit20': float((pr[top] <= 20).mean()), 'b_bias': d[bot].mean(),
                  'f_bias': -d[pr <= 10].mean(), 'mae': d.abs().mean(), 'n': len(g), 'spearman': g.pred.corr(g.actual_gih, method='spearman')}
    return pd.DataFrame(out).T


def summarize(P):
    n = P.n
    return {'t_bias': float(P.t_bias.mean()), 't_mae': float(P.t_mae.mean()), 'hit20': float(P.hit20.mean()), 'b_bias': float(P.b_bias.mean()),
            'f_bias': float(P.f_bias.mean()), 'pooled_mae': float((P.mae * n).sum() / n.sum()), 'spearman': float(P.spearman.mean())}


def evaluate():
    ref = pd.read_csv(ROOT / 'research/c9_power_questions/oof_B10.csv.gz')
    arms = {'B10': ref}
    for k in ('B10SC', 'shuf', 'B10re'):
        f = HERE / f'oof_{k}.csv.gz'
        if f.exists():
            arms[k] = pd.read_csv(f)
    P = {k: e1_per_set(v) for k, v in arms.items()}
    res = {k: summarize(p) for k, p in P.items()}
    b = P['B10']
    for k, p in P.items():
        res[k]['sets_mae_lower'] = int((p.mae < b.mae).sum())
        res[k]['sets_t_mae_lower'] = int((p.t_mae < b.t_mae).sum())
        res[k]['mae_gain_pp'] = res['B10']['pooled_mae'] - res[k]['pooled_mae']
        res[k]['t_mae_gain_pp'] = res['B10']['t_mae'] - res[k]['t_mae']
    if 'B10SC' in res:
        r, r0 = res['B10SC'], res['B10']
        rule = {'mae_gain_ge_0.01': r['mae_gain_pp'] >= 0.01, 'spearman_not_worse': r['spearman'] >= r0['spearman'],
                'sets_ge_15': r['sets_mae_lower'] >= 15,
                'e1_t_mae_not_worse': r['t_mae'] <= r0['t_mae'], 'e1_hit20_not_lower': r['hit20'] >= r0['hit20'],
                'e1_abs_t_bias_not_larger': abs(r['t_bias']) <= abs(r0['t_bias']), 'e1_f_bias_guard': r['f_bias'] - r0['f_bias'] <= 0.5}
        if 'shuf' in res:
            rule['control_gain_lt_half'] = res['shuf']['mae_gain_pp'] < r['mae_gain_pp'] / 2
        rule['pass'] = all(rule.values())
        res['rule_g1_loso'] = rule
        pset = {s: {'B10': float(b.mae[s]), 'B10SC': float(P['B10SC'].mae[s])} for s in b.index}
        res['per_set_mae'] = pset
        # by whether the card carries a support reference
        pool, *_ = load_pool()
        flag = pool.set_index(['set', 'name'])['sc_n_sup'] > 0
        for k in ('B10', 'B10SC'):
            d = arms[k].assign(flag=[flag.get((s, n), False) for s, n in zip(arms[k]['set'], arms[k]['name'])])
            d['ae'] = (d.pred - d.actual_gih).abs() * 100
            res[f'mae_by_ref_{k}'] = {'with_support_ref': float(d[d.flag].ae.mean()), 'n_with': int(d.flag.sum()), 'without': float(d[~d.flag].ae.mean())}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set_mae'}, indent=1, default=float))


def fra_frame(fra_path, pool, base, cols):
    """FRA feature frame with the B5 + C9 columns (as research/c9_power_questions/freeze_fra.py) and the set-context columns."""
    fra, f = e.fra_frame(fra_path, base, cols, pool)
    keys = [f"FRA|{c['id']}" for c in fra]
    for src, names in ((c5.C4DIR / 'c4_features.csv.gz', c5.C4_NUM + c5.C4_ROLE), (c5.HERE / 'c5_features.csv.gz', c5.TAGC + c5.SCALE + c5.CNT),
                       (ROOT / 'research/c9_power_questions/c9_features.csv.gz', c9.MEAN + c9.SD + c9.SUM)):
        t = pd.read_csv(src).set_index('key')
        assert all(k in t.index for k in keys)
        for c in names:
            f[c] = t.loc[keys, c].to_numpy(dtype=float)
    sc = pd.read_csv(HERE / 'sc_features.csv.gz').set_index('key')
    # the 10 lands of rarity 'land' (basic-slot lands) of the FRA card file are not in the set lists: no reference, zeros
    missing = [k for k in keys if k not in sc.index]
    assert len(missing) == 10 and all('Land' in c['type_line'] for c, k in zip(fra, keys) if k in missing), missing
    for c in SC:
        f[c] = [float(sc.loc[k, c]) if k in sc.index else 0.0 for k in keys]
    return fra, f, keys


def new_c9_columns(f, keys):
    """Replace the 17 C9 columns of the judged FRA cards by the plan-1 answers (3 passes; same formulas as c9.features)."""
    jc = pd.read_csv(HERE / 'judge_cards.csv')
    raws = [json_raw(p) for p in ('p1', 'p2', 'p3')]
    g = f.copy()
    moved = []
    for r in jc.itertuples():
        if r.is_anchor:
            continue
        v = np.array([raws[i][r.id] for i in range(3)], float)
        m, s = v.mean(0), v.std(0)
        i = keys.index(r.key)
        old = g.loc[i, c9.MEAN].to_numpy(float).copy()
        g.loc[i, c9.MEAN] = m
        g.loc[i, c9.SD] = s
        g.loc[i, 'c9_impuna'] = m[0] + m[1]
        g.loc[i, 'c9_valfloor'] = m[2] + m[3]
        g.loc[i, 'c9_bomb'] = m[6] - 1.25 * m[5]
        moved.append(dict(key=r.key, id=r.id, **{f'old_{k}': o for k, o in zip(c9.F, old)}, **{f'new_{k}': x for k, x in zip(c9.F, m)}))
    return g, pd.DataFrame(moved)


def json_raw(p):
    sys.path.insert(0, str(HERE))
    import g1_inputs as gi
    raw, errs = gi.load_raw(p)
    assert not errs, errs
    return raw


def freeze(which, fra_path):
    """which: arm2 (set-context features, no AI) | arm1 (new judgments, B10 model) | arm12 (both). Writes fra_frozen_<which>.csv/.json."""
    import hashlib
    pool, base, cols, nums10, _ = load_pool()
    fra, f, keys = fra_frame(fra_path, pool, base, cols)
    nums = nums10 + SC if which in ('arm2', 'arm12') else nums10
    if which in ('arm1', 'arm12'):
        f, moved = new_c9_columns(f, keys)
        moved.to_csv(HERE / 'grade_moves.csv', index=False)
    _, _, _, p = e.predict(pool, f, nums)
    out = pd.DataFrame({'id': [c['id'] for c in fra], 'name': [c['name'] for c in fra]})
    base0 = pd.read_csv(ROOT / 'research/c9_power_questions/fra_frozen_predictions.csv').set_index('id')
    out['pred_B10_frozen'] = out['id'].map(base0['pred_B10'])
    out[f'pred_{which}'] = p
    if which == 'arm2':    # drift check: the frozen B10 re-predicted in this environment
        _, _, _, p0 = e.predict(pool, f, nums10)
        out['pred_B10_rerun'] = p0
    assert out.notna().all().all()
    out.to_csv(HERE / f'fra_frozen_{which}.csv', index=False)
    meta = {'arm': which, 'seeds': list(SEEDS), 'n_features': len(nums), 'sha256': hashlib.sha256((HERE / f'fra_frozen_{which}.csv').read_bytes()).hexdigest(),
            'mean_abs_diff_vs_frozen_B10_pp': float((out[f'pred_{which}'] - out['pred_B10_frozen']).abs().mean() * 100),
            'corr_vs_frozen_B10': float(np.corrcoef(out[f'pred_{which}'], out['pred_B10_frozen'])[0, 1])}
    if 'pred_B10_rerun' in out:
        meta['rerun_B10_mean_abs_diff_vs_frozen_pp'] = float((out['pred_B10_rerun'] - out['pred_B10_frozen']).abs().mean() * 100)
    json.dump(meta, open(HERE / f'fra_frozen_{which}.json', 'w'), indent=1)
    print(meta)


if __name__ == '__main__':
    if sys.argv[1] == 'freeze':
        freeze(sys.argv[2], Path(sys.argv[3]))
    else:
        {'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
