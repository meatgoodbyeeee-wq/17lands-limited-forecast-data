"""C6 vocabulary gap tags vs C5 (Rule F6, see PLAN.md).

  python3 c6.py features
  python3 c6.py arm <B6|B6_no_c4|B6_common>
  python3 c6.py evaluate
"""
import glob, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/production_c3'))
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects'))
import c5  # noqa: E402  (imports check_raw first, then export_gih_c3_28set)
e = c5.e

# name -> (regex on text with reminder text removed, applied to text; optional type-line regex)
RULES = {
    'poison': (r'\btoxic\b|poison counter|\binfect\b|\bcorrupted\b|\bpoisoned\b', None),
    'prolif': (r'\bproliferate\b', None),
    'minus_ctr': (r'-1/-1 counter', None),
    'defender': (r'\bdefender\b', None),
    'transform': (r'\btransform|\bdaybound\b|\bnightbound\b|becomes? (day|night)|//\s*\w+\s*//|\bdisturb\b', None),
    'gyhate': (r'exile (target|all|each|up to \w+ target)[^.]*graveyard|exile target card from a graveyard|cards? in (all )?graveyards?|each (player|opponent)\'s graveyard', None),
    'ncremoval': (r'(destroy|exile|return) (up to \w+ )?target (nonland |nonbasic |tapped |untapped )?(artifact|enchantment|permanent|planeswalker|land|battle)', None),
    'prevent': (r'\bprevent (all|the next|that|\d+|any)', None),
    'monarch': (r'\bmonarch\b|\binitiative\b|ring tempts|\bgoad\b|\bdungeon\b', None),
    'altcost': (r'\b(evoke|dash|blitz|emerge|escape|disturb|madness|miracle|overload|spectacle|mutate|foretell|plot|warp|sneak|ninjutsu|prototype|unearth|offspring)\b', None),
    'facedown': (r'\bmanifest|\bcloak\b|\bdisguise\b|\bmorph\b|\bmegamorph\b|face[- ]down', None),
    'saga': (r'^$', r'\bSaga\b'),
    'classroom': (r'^$', r'\b(Class|Room)\b'),
    'lifegain': (r'\byou gain [^.]*\blife\b|\bgains? (\d+|x|that much) life|\bgain life\b|\bgains? life equal', None),
    'protect': (r'protection from|\bindestructible\b|\bregenerate\b', None),
    'legend': (r'^$', r'\bLegendary\b'),
}
G6 = [f'g6_{k}' for k in RULES]


def strip_reminder(t):
    return re.sub(r'\([^)]*\)', ' ', t)


def tag_row(btext, type_line):
    t = strip_reminder(btext).lower()
    out = {}
    for k, (pat, tp) in RULES.items():
        if tp is not None:
            out[f'g6_{k}'] = int(bool(re.search(tp, type_line)))
        else:
            out[f'g6_{k}'] = int(bool(re.search(pat, t, re.I)))
    return out


def features():
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    rows = []
    for r in u.itertuples():
        d = {c: 0 for c in G6} if r.auto == 1 else tag_row(r.btext, r.type_line)
        for k in str(r.keys).split(';'):
            rows.append({'key': k, **d})
    t = pd.DataFrame(rows)
    assert not t['key'].duplicated().any()
    t.to_csv(HERE / 'c6_features.csv.gz', index=False, compression='gzip')
    prev = t[G6].mean().sort_values()
    json.dump({k: float(v) for k, v in prev.items()}, open(HERE / 'prevalence.json', 'w'), indent=1)
    print(prev.round(4).to_string())


def load_pool():
    pool, base, cols, miss = c5.load_pool()
    g = pd.read_csv(HERE / 'c6_features.csv.gz')
    pool = pool.merge(g, on='key', how='left')
    assert pool[G6[0]].isna().mean() < 0.03
    pool[G6] = pool[G6].fillna(0)
    return pool, base, cols, miss


def arm_nums(name, base, cols):
    b5 = c5.arm_nums('B5', base, cols)
    prev = json.load(open(HERE / 'prevalence.json'))
    common = [c for c in G6 if prev[c] >= 0.01]
    return {'B6': b5 + G6, 'B6_no_c4': c5.arm_nums('A_C5', base, cols) + G6, 'B6_common': b5 + common}[name]


def run_arm(name):
    pool, base, cols, miss = load_pool()
    nums = arm_nums(name, base, cols)
    seeds = c5.SEEDS if name == 'B6' else c5.SEEDS[:1]
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
        for ref in ('B5', 'A'):
            res[k][f'sets_lower_mae_vs_{ref}'] = int(sum(per[k][s]['mae_pp'] < per[ref][s]['mae_pp'] for s in per[k]))
    if 'B6' in arms:
        b5, b6 = res['B5'], res['B6']
        res['rule_f6'] = {'mae': b6['pooled_mae_pp'] < b5['pooled_mae_pp'], 'spearman': b6['spearman_mean'] > b5['spearman_mean'],
                          'sets': b6['sets_lower_mae_vs_B5'] >= 15, 'gain': b5['pooled_mae_pp'] - b6['pooled_mae_pp'] > 0.01}
        res['rule_f6']['pass'] = all(res['rule_f6'].values())
        key = lambda d: d['set'] + '|' + d['name']
        m = arms['B5'].assign(k=key(arms['B5'])).merge(arms['B6'].assign(k=key(arms['B6']))[['k', 'pred']].rename(columns={'pred': 'p6'}), on='k')
        res['by_rarity'] = {int(r): {'B5': float((g['pred'] - g['actual_gih']).abs().mean() * 100),
                                     'B6': float((g['p6'] - g['actual_gih']).abs().mean() * 100)} for r, g in m.groupby('rarity_ord')}
        res['per_set'] = {s: {'B5': per['B5'][s], 'B6': per['B6'][s]} for s in per['B6']}
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    {'features': features, 'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
