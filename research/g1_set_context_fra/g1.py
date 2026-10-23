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


if __name__ == '__main__':
    {'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
