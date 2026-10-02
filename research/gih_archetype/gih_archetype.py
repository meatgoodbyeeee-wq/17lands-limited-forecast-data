"""Card GIH: official-archetype features (ARCH) and C3 ablations, Rule G (see PLAN.md).

  python3 research/gih_archetype/gih_archetype.py arm <name>     # writes oof_<name>.csv.gz
  python3 research/gih_archetype/gih_archetype.py check          # re-runs one fold of A against production OOF
  python3 research/gih_archetype/gih_archetype.py evaluate
"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
import export_gih_c3_28set as e  # noqa: E402

LAB = ROOT / 'research/archetype_labels'
ORDER = 'WUBRG'
ARCH = ['arch_in', 'arch_P', 'arch_E', 'arch_n', 'arch_support', 'arch_payoffs', 'arch_P_x_support', 'arch_gold_fit', 'arch_colour_flex']
SEEDS = e.SEEDS


def norm(c):
    c = str(c).strip()
    return '' if c in ('', 'none') else ''.join(x for x in ORDER if x in c)


def inside(colors, code):
    return all(x in code for x in colors)


def arch_table(s, inp, raw, rarity_cu):
    """inp: input rows (id,name,colors,...), raw: labels, rarity_cu: bool array aligned with inp (common/uncommon)."""
    d = inp.merge(raw, on='id', validate='one_to_one')
    d['prim'] = d['primary'].map(norm)
    d['secs'] = d['secondary'].map(lambda x: [norm(c) for c in str(x).split('+') if norm(c)])
    codes = sorted({c for c in d['prim'] if c} | {c for l in d['secs'] for c in l})
    cu = np.asarray(rarity_cu, bool)
    ncu = max(cu.sum(), 1)
    fits_any = d.apply(lambda r: [r['prim']] + r['secs'] if r['prim'] else r['secs'], axis=1)
    out = pd.DataFrame(index=d.index)
    out['arch_in'] = (d['prim'] != '').astype(float)
    out['arch_P'] = (d['role'] == 'P').astype(float) * out['arch_in']
    out['arch_E'] = (d['role'] == 'E').astype(float) * out['arch_in']
    out['arch_n'] = fits_any.map(len).astype(float)
    sup, pay = [], []
    for i, r in d.iterrows():
        k = r['prim']
        if not k:
            sup.append(0.0); pay.append(0.0); continue
        others = cu & (d.index != i)
        sup.append(float((others & (d['role'] == 'E') & fits_any.map(lambda l: k in l)).sum()) / ncu)
        pay.append(float((others & (d['role'] == 'P') & (d['prim'] == k)).sum()) / ncu)
    out['arch_support'] = sup
    out['arch_payoffs'] = pay
    out['arch_P_x_support'] = out['arch_P'] * out['arch_support']
    col = d['colors'].fillna('').astype(str)
    out['arch_gold_fit'] = ((col.str.len() >= 2) & (col.map(lambda c: ''.join(x for x in ORDER if x in c)) == d['prim'])).astype(float)
    out['arch_colour_flex'] = col.map(lambda c: float(sum(inside(c, k) for k in codes)))
    out['set'] = s
    out['name'] = d['name'].values
    return out


def rarity_cu_for(pool_set, inp):
    r = pool_set.drop_duplicates('name').set_index('name')['rarity_ord']
    return inp['name'].map(r).fillna(9).values <= 1


def load_pool():
    pool, base, cols = e.training()
    feats = []
    for s in sorted(pool['set'].unique()):
        inp = pd.read_csv(LAB / f'input/{s}.csv', keep_default_na=False)
        raw = pd.read_csv(LAB / f'raw/{s}.csv', keep_default_na=False, dtype=str)
        feats.append(arch_table(s, inp, raw, rarity_cu_for(pool[pool['set'] == s], inp)))
    a = pd.concat(feats).drop_duplicates(['set', 'name'])
    pool = pool.merge(a, on=['set', 'name'], how='left')
    cover = float(pool['arch_in'].notna().mean())
    pool[ARCH] = pool[ARCH].fillna(0.0)
    return pool, base, cols, cover


C3_GROUPS = {
    'raw10': ['llm_removal', 'llm_sweeper', 'llm_bodies', 'llm_cards', 'llm_repeat', 'llm_modal', 'llm_dependency', 'llm_drawback', 'llm_trick', 'llm_sink'],
    'dep12': [f'llm_dep_{x}' for x in 'TGAESKCLXHMO'],
    'comp4': ['llm_impact', 'llm_friction', 'llm_net', 'llm_impact_per_mv'],
}


def arm_features(name, base, cols):
    if name == 'A' or name == 'A_s1':
        return base + cols
    if name == 'B':
        return base + cols + ARCH
    if name == 'B_nocontext':
        return base + cols + [c for c in ARCH if c not in ('arch_support', 'arch_payoffs', 'arch_P_x_support')]
    if name.startswith('drop_'):
        g = C3_GROUPS[name[5:]]
        return base + [c for c in cols if c not in g]
    raise SystemExit(name)


def run_arm(name):
    pool, base, cols, cover = load_pool()
    nums = arm_features(name, base, cols)
    seeds = SEEDS if name in ('A', 'B') else [SEEDS[0]]
    pred = np.full(len(pool), np.nan)
    for s in sorted(pool['set'].unique()):
        te = (pool['set'] == s).to_numpy()
        ps = []
        for sd in seeds:
            c, t, x = e.parts(pool[~te], pool[te], nums, sd)
            ps.append(c + 1.25 * (.7 * t + .3 * x - c))
        pred[te] = np.mean(ps, axis=0)
        print(name, s, flush=True)
    out = pool[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=pred)
    out.to_csv(HERE / f'oof_{name}.csv.gz', index=False, compression='gzip')
    json.dump({'coverage': cover, 'n_features': len(nums), 'seeds': seeds}, open(HERE / f'meta_{name}.json', 'w'))


def check():
    pool, base, cols, _ = load_pool()
    s = 'AFR'
    te = (pool['set'] == s).to_numpy()
    p = np.mean([(lambda c, t, x: c + 1.25 * (.7 * t + .3 * x - c))(*e.parts(pool[~te], pool[te], base + cols, sd)) for sd in SEEDS], axis=0)
    ref = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    m = pool.loc[te, ['set', 'name']].assign(p=p).merge(ref, on=['set', 'name'])
    print('max abs diff', float((m['p'] - m['pred']).abs().max()))


def metrics(df):
    per = {s: {'mae_pp': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
               'spearman': float(spearmanr(g['pred'], g['actual_gih']).correlation)} for s, g in df.groupby('set')}
    return {'pooled_mae_pp': float((df['pred'] - df['actual_gih']).abs().mean() * 100),
            'spearman_mean': float(np.mean([v['spearman'] for v in per.values()]))}, per


def evaluate():
    ref = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')[['set', 'name', 'pred']].rename(columns={'pred': 'prodA'})
    res = {}
    arms = {Path(f).name[4:-7]: pd.read_csv(f) for f in sorted(glob.glob(str(HERE / 'oof_*.csv.gz')))}
    if 'A' not in arms:
        arms['A'] = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    per = {}
    for k, df in arms.items():
        res[k], per[k] = metrics(df)
    def wins(k, ref_):
        return int(sum(per[k][s]['mae_pp'] < per[ref_][s]['mae_pp'] for s in per[k]))
    for k in arms:
        if k != 'A':
            res[k]['sets_lower_mae_vs_A' if k == 'B' else 'sets_lower_mae_vs_A_s1'] = wins(k, 'A' if k == 'B' or 'A_s1' not in arms else 'A_s1')
    if 'B' in arms:
        b, a = res['B'], res['A']
        res['by_rarity'] = {int(r): {'A': float((g['pred'] - g['actual_gih']).abs().mean() * 100)} for r, g in arms['A'].groupby('rarity_ord')}
        for r, g in arms['B'].groupby('rarity_ord'):
            res['by_rarity'][int(r)]['B'] = float((g['pred'] - g['actual_gih']).abs().mean() * 100)
        res['rule_g'] = {'mae': b['pooled_mae_pp'] < a['pooled_mae_pp'], 'spearman': b['spearman_mean'] > a['spearman_mean'],
                         'sets': b['sets_lower_mae_vs_A'] >= 15, 'gain': a['pooled_mae_pp'] - b['pooled_mae_pp'] > 0.01}
        res['rule_g']['pass'] = all(res['rule_g'].values())
        res['per_set'] = {s: {'A': per['A'][s], 'B': per['B'][s]} for s in per['B']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'arm': lambda: run_arm(sys.argv[2]), 'check': check, 'evaluate': evaluate}[sys.argv[1]]()
