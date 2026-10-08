"""C8 step 2: card x set-environment features from the step-1 profiles (no AI, no outcomes).

  python3 env.py features      -> c8_features.csv.gz (real environment + wrong-environment control)
  python3 env.py arm <B8|B8_removal|B8_combat|B8_perf|B8_wrongenv>
  python3 env.py evaluate

Every other card of the same set is weighted by the expected number of copies a drafter sees per 3 packs
(booster layout by rarity, as in C7c). The card itself is excluded from its own environment.
"""
import glob, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/c7c_draft_weighted'))
import c7c  # noqa: E402
c5, e = c7c.c5, c7c.e

FEAT = ['ans_w', 'ans_share', 'ans_cheap_share', 'reach_share', 'reach_threat_share',
        'atk_survive', 'blk_kill', 'blk_survive', 'stat_rank_mv', 'set_removal_density',
        'blockable_share', 'trick_flip', 'protect_env', 'token_sweep_risk', 'lifegain_env', 'aura_risk']
REMOVAL_F = FEAT[:5] + ['set_removal_density']
COMBAT_F = FEAT[5:9] + ['blockable_share']
PERF_F = ['trick_flip', 'protect_env', 'token_sweep_risk', 'lifegain_env', 'aura_risk']
SINGLE_KINDS = {'dmg', 'destroy', 'exile', 'shrink', 'bite', 'pacify'}
NA = -1.0
KIND_BASE = {'dmg': 1.0, 'shrink': 1.0, 'destroy': 1.0, 'exile': 1.0, 'bite': 0.7, 'edict': 0.25, 'bounce': 0.25, 'pacify': 0.7, 'tap': 0.15}
COLOR = {'white': 'W', 'blue': 'U', 'black': 'B', 'red': 'R', 'green': 'G'}


def kill(eff, c):
    """value in [0,1] that removal effect eff answers creature profile c (dict)."""
    if not c['is_creature'] or c['toughness'] is None or np.isnan(c['toughness']):
        return 0.0
    T, P, mv = c['toughness'], c['power'], c['mv']
    k = eff['kind']
    for key, ok in (('mv_le', mv <= eff.get('mv_le', 99)), ('mv_ge', mv >= eff.get('mv_ge', -1)),
                    ('pow_ge', (P if P == P else 0) >= eff.get('pow_ge', -99)), ('pow_le', (P if P == P else 0) <= eff.get('pow_le', 99)),
                    ('tou_ge', T >= eff.get('tou_ge', -99)), ('tou_le', T <= eff.get('tou_le', 99))):
        if key in eff and not ok:
            return 0.0
    if eff.get('flying_only') and not c['kw_flying']:
        return 0.0
    if eff.get('nonflying_only') and c['kw_flying']:
        return 0.0
    if eff.get('token_only'):
        return 0.0
    if 'not_color' in eff and COLOR[eff['not_color']] in c['colors']:
        return 0.0
    if 'color_only' in eff and COLOR[eff['color_only']] not in c['colors']:
        return 0.0
    v = KIND_BASE[k]
    if k in ('dmg',):
        v = v if T <= eff['amount'] and not c['kw_indestructible'] else 0.0
    elif k == 'shrink':
        v = v if T <= eff['amount'] else 0.0
    elif k == 'bite':
        v = v if T <= eff['amount'] and not c['kw_indestructible'] else 0.0
    elif k == 'destroy':
        v = 0.0 if c['kw_indestructible'] else v
    elif k == 'exile' and eff.get('temporary'):
        v = 0.8
    if eff['scope'] == 'single':
        if c['kw_hexproof']:
            v = 0.0
        elif c['kw_protection']:
            v *= 0.5
        elif c['kw_ward']:
            v *= 0.7
    if eff['scope'] == 'sweep':
        v *= 0.6
    if eff.get('tapped_only') or eff.get('combat_only'):
        v *= 0.6
    if eff.get('setup'):
        v *= 0.8
    return float(v)


def best_kill(effs, c):
    return max((kill(x, c) for x in effs), default=0.0)


def can_block(att, blk):
    if att['kw_unblockable']:
        return False
    if att['kw_flying'] and not (blk['kw_flying'] or blk['kw_reach']):
        return False
    if blk['kw_cant_block']:
        return False
    return True


def fight(a, b):
    """simultaneous combat a vs b (a attacking or blocking b). returns (a_dies, b_dies)."""
    pa, ta, pb, tb = a['power'], a['toughness'], b['power'], b['toughness']
    a_kills = pa > 0 and (pa >= tb or a['kw_deathtouch']) and not b['kw_indestructible']
    b_kills = pb > 0 and (pb >= ta or b['kw_deathtouch']) and not a['kw_indestructible']
    if a['kw_first_strike'] and not b['kw_first_strike'] and a_kills:
        b_kills = False
    if b['kw_first_strike'] and not a['kw_first_strike'] and b_kills:
        a_kills = False
    return b_kills, a_kills


def set_features(g, w):
    """g: profiles of one set (DataFrame), w: weights aligned. returns DataFrame of FEAT."""
    n = len(g)
    recs = g.to_dict('records')
    for r in recs:
        r['effs'] = json.loads(r['removal'])
        for k in ('power', 'toughness'):
            r[k] = float(r[k]) if r[k] == r[k] and r[k] is not None else np.nan
    is_cr = np.array([r['is_creature'] == 1 and r['toughness'] == r['toughness'] and r['power'] == r['power'] for r in recs])
    is_rm = np.array([len(r['effs']) > 0 for r in recs])
    rar = g['rarity'].to_numpy()
    K = np.zeros((n, n))           # K[j, i] = removal j answers creature i
    for j in np.where(is_rm)[0]:
        for i in np.where(is_cr)[0]:
            if i != j:
                K[j, i] = best_kill(recs[j]['effs'], recs[i])
    out = {f: np.full(n, NA) for f in FEAT}
    w_rm = w * is_rm
    cheap = np.array([r['mv'] <= 3 for r in recs])
    tot_rm = w_rm.sum()
    out['set_removal_density'][:] = tot_rm
    for i in np.where(is_cr)[0]:
        mask = np.arange(n) != i
        den = (w_rm * mask).sum()
        out['ans_w'][i] = float((w_rm * K[:, i] * mask).sum())
        out['ans_share'][i] = out['ans_w'][i] / den if den else 0.0
        dc = (w_rm * cheap * mask).sum()
        out['ans_cheap_share'][i] = float((w_rm * cheap * K[:, i] * mask).sum() / dc) if dc else 0.0
    w_cr = w * is_cr
    threat = is_cr & ((rar >= 2) | np.array([(r['power'] if r['power'] == r['power'] else 0) >= 4 for r in recs]))
    for j in np.where(is_rm)[0]:
        mask = np.arange(n) != j
        den = (w_cr * mask).sum()
        out['reach_share'][j] = float((w_cr * K[j] * mask).sum() / den) if den else 0.0
        wt = w * threat * mask
        out['reach_threat_share'][j] = float((wt * K[j]).sum() / wt.sum()) if wt.sum() else 0.0
    idx = np.where(is_cr)[0]
    for i in idx:
        a = recs[i]
        sa = sk = ss = den = 0.0
        for o in idx:
            if o == i:
                continue
            b, wo = recs[o], w[o]
            den += wo
            # i attacks, o may block
            if not can_block(a, b):
                sa += wo
            else:
                a_dies, _ = fight(a, b)
                sa += wo * (not a_dies)
            # o attacks, i blocks
            if can_block(b, a):
                i_dies, o_dies = fight(a, b)
                sk += wo * o_dies
                ss += wo * (not i_dies)
        if den:
            out['atk_survive'][i], out['blk_kill'][i], out['blk_survive'][i] = sa / den, sk / den, ss / den
    # stat rank: (P+T) percentile among creatures of the same set with the same mana value (weighted, self excluded)
    for i in idx:
        same = [o for o in idx if o != i and recs[o]['mv'] == recs[i]['mv']]
        if not same:
            out['stat_rank_mv'][i] = 0.5
            continue
        si = recs[i]['power'] + recs[i]['toughness']
        so = np.array([recs[o]['power'] + recs[o]['toughness'] for o in same]); wo = w[same]
        out['stat_rank_mv'][i] = float(((so < si) * wo).sum() + 0.5 * ((so == si) * wo).sum()) / wo.sum()
    # ---- performance x environment
    def wmed(x, wt):
        o = np.argsort(x); x, wt = x[o], wt[o]
        c = np.cumsum(wt)
        return float(x[np.searchsorted(c, c[-1] / 2)]) if c[-1] > 0 else float(np.median(x))
    P = np.array([r['power'] if is_cr[k] else 0.0 for k, r in enumerate(recs)])
    T = np.array([r['toughness'] if is_cr[k] else 0.0 for k, r in enumerate(recs)])
    wc = w * is_cr
    single = np.array([any(x['scope'] == 'single' and x['kind'] in SINGLE_KINDS for x in r['effs']) for r in recs])
    sweep = np.array([any(x['scope'] != 'single' and x['kind'] in ('dmg', 'shrink', 'destroy', 'exile') for x in r['effs']) for r in recs])
    for i in range(n):
        r = recs[i]
        mask = np.arange(n) != i
        wcm = wc * mask
        tot_c = wcm.sum()
        if is_cr[i] and tot_c:
            out['blockable_share'][i] = float(sum(wcm[o] for o in idx if o != i and can_block(r, recs[o])) / tot_c)
        if (r['trick_p'] or r['trick_t']) and tot_c:
            Pm, Tm = wmed(P[is_cr & mask], w[is_cr & mask]), wmed(T[is_cr & mask], w[is_cr & mask])
            kill = ((T > Pm) & (T <= Pm + r['trick_p']) & is_cr & mask) * w
            save = ((P >= Tm) & (P < Tm + r['trick_t']) & is_cr & mask) * w
            out['trick_flip'][i] = float((kill.sum() + save.sum()) / tot_c)
        sr = float((w * single * mask).sum())
        if r['protect']:
            out['protect_env'][i] = sr
        if 'Aura' in r['type_line'] and re.search(r'enchant creature', str(r['btext']).lower()):
            out['aura_risk'][i] = sr
        if r['token_n']:
            out['token_sweep_risk'][i] = float(r['token_n'] * (w * sweep * mask).sum())
        if r['lifegain_n'] and tot_c:
            cheap_cr = is_cr & mask & (np.array([x['mv'] for x in recs]) <= 3)
            agg = float((w * cheap_cr * P).sum() / max((w * cheap_cr).sum(), 1e-9))
            evas = float((wcm * np.array([x['kw_flying'] or x['kw_menace'] or x['kw_trample'] for x in recs])).sum() / tot_c)
            out['lifegain_env'][i] = float(r['lifegain_n'] * (agg + evas))
    return pd.DataFrame(out, index=g.index)


def table():
    p = pd.read_csv(HERE / 'profiles.csv.gz', keep_default_na=False, na_values=[''])
    p['colors'] = p['colors'].fillna('')
    rows = []
    for r in p.itertuples():
        for k in str(r.keys).split(';'):
            rows.append({'key': k, 'set': k.split('|')[0], **{c: getattr(r, c) for c in p.columns if c not in ('keys',)}})
    t = pd.DataFrame(rows)
    rar = c7c.rarity_map(c7c.FRA_DEFAULT)
    t = t[t['key'].isin(rar)].reset_index(drop=True)          # drops basics / non-booster
    t['rarity'] = t['key'].map(rar)
    t['w'], _ = c7c.weights(list(t['key']), rar)
    return t


def features():
    t = table()
    real = pd.concat([set_features(g, g['w'].to_numpy()) for _, g in t.groupby('set')]).reindex(t.index)
    # wrong-environment control: each set is evaluated against the pool of another set (fixed derangement, seed 20261005)
    sets = sorted(t['set'].unique())
    rng = np.random.default_rng(20261005)
    while True:
        perm = rng.permutation(len(sets))
        if all(perm[i] != i for i in range(len(sets))):
            break
    other = {s: sets[perm[i]] for i, s in enumerate(sets)}
    wrong = []
    for s in sets:
        g, h = t[t['set'] == s], t[t['set'] == other[s]]
        both = pd.concat([g, h])
        f = set_features(both.reset_index(drop=False).set_index('index'), np.r_[np.zeros(len(g)), h['w'].to_numpy()])
        wrong.append(f.loc[g.index])
    wrong = pd.concat(wrong).reindex(t.index)
    out = pd.concat([t[['key']], real.add_prefix('c8_'), wrong.add_prefix('c8w_')], axis=1)
    out.to_csv(HERE / 'c8_features.csv.gz', index=False, compression='gzip')
    json.dump(other, open(HERE / 'wrongenv_map.json', 'w'), indent=1)
    print(out.filter(like='c8_').replace(NA, np.nan).describe().round(3).T.to_string())


FEATC = [f'c8_{f}' for f in FEAT]
FEATW = [f'c8w_{f}' for f in FEAT]


def load_pool():
    pool, base, cols, miss = c5.load_pool()
    g = pd.read_csv(HERE / 'c8_features.csv.gz')
    pool = pool.merge(g, on='key', how='left')
    assert pool[FEATC[0]].isna().mean() < 0.03
    pool[FEATC + FEATW] = pool[FEATC + FEATW].fillna(NA)
    return pool, base, cols, miss


def arm_nums(name, base, cols):
    b5 = c5.arm_nums('B5', base, cols)
    return {'B8': b5 + FEATC, 'B8_removal': b5 + [f'c8_{f}' for f in REMOVAL_F],
            'B8_combat': b5 + [f'c8_{f}' for f in COMBAT_F], 'B8_perf': b5 + [f'c8_{f}' for f in PERF_F],
            'B8_wrongenv': b5 + FEATW}[name]


def run_arm(name):
    pool, base, cols, miss = load_pool()
    nums = arm_nums(name, base, cols)
    seeds = c5.SEEDS if name == 'B8' else c5.SEEDS[:1]
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
    arms['B5'] = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')
    res, per = {}, {}
    for k, df in arms.items():
        res[k], per[k] = c5.metrics(df)
    for k in arms:
        if k == 'B5':
            continue
        res[k]['sets_lower_mae_vs_B5'] = int(sum(per[k][s]['mae_pp'] < per['B5'][s]['mae_pp'] for s in per[k]))
        res[k]['mae_gain_vs_B5_pp'] = res['B5']['pooled_mae_pp'] - res[k]['pooled_mae_pp']
    if 'B8' in arms:
        b5, b = res['B5'], res['B8']
        r = {'mae': b['pooled_mae_pp'] < b5['pooled_mae_pp'], 'spearman': b['spearman_mean'] > b5['spearman_mean'],
             'sets': b['sets_lower_mae_vs_B5'] >= 15, 'gain': b5['pooled_mae_pp'] - b['pooled_mae_pp'] > 0.01}
        if 'B8_wrongenv' in arms:
            r['control_below_half'] = res['B8_wrongenv']['mae_gain_vs_B5_pp'] < 0.5 * b['mae_gain_vs_B5_pp']
        r['pass'] = all(r.values())
        res['rule_f8'] = r
        key = lambda d: d['set'] + '|' + d['name']
        m = arms['B5'].assign(k=key(arms['B5'])).merge(arms['B8'].assign(k=key(arms['B8']))[['k', 'pred']].rename(columns={'pred': 'p8'}), on='k')
        res['by_rarity'] = {int(q): {'B5': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
                                     'B8': float((g['p8'] - g['actual_gih']).abs().mean() * 100)} for q, g in m.groupby('rarity_ord')}
        rm = m[m['rarity_ord'] >= 2]
        res['rare_mythic_mae'] = {'B5': float((rm['pred'] - rm['actual_gih']).abs().mean() * 100), 'B8': float((rm['p8'] - rm['actual_gih']).abs().mean() * 100)}
        res['per_set'] = {s: {'B5': per['B5'][s], 'B8': per['B8'][s]} for s in per['B8']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
