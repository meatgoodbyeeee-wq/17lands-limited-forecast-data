"""DA1 part A: do N2b primary pairs agree more after deck adjustment? python3 da1_a.py"""
import json, subprocess
from pathlib import Path
import numpy as np, pandas as pd
from n2_prep import *   # load(), C9  (copied unchanged from branch research/n2-near-duplicate)
HERE = Path(__file__).resolve().parent
c, X, v = load()
o = pd.read_csv(C9 / 'oof_B10.csv.gz'); o['key'] = o.set + '|' + o.name
m = pd.DataFrame([(k, i) for i, r in enumerate(c.itertuples()) for k in r.keys.split(';')], columns=['key', 'ci'])
o = o.merge(m, on='key', validate='1:1').merge(c[['cat', 'mv', 'ntok', 'pt']], left_on='ci', right_index=True).reset_index(drop=True)
Xo = X[o.ci.to_numpy()]; sim = (Xo @ Xo.T).toarray()
A = lambda col: o[col].to_numpy().astype(object)
mv = o.mv.to_numpy(); cat = A('cat'); pt = A('pt')
same = lambda a: a[:, None] == a[None, :]
base = same(cat) & ~same(A('set')) & ~same(A('name'))
tk = o.ntok.to_numpy() >= 6; base &= tk[:, None] & tk[None, :]
mv1 = np.abs(mv[:, None] - mv[None, :]) <= 1
iscr = (cat == 'Creature'); isld = (cat == 'Land')
ok = (base & iscr[:, None] & (sim >= 0.95) & same(mv) & same(pt)) | (base & ~iscr[:, None] & ~isld[:, None] & mv1 & (sim >= 0.95))
n = ok.sum(1); has = n > 0
ref = subprocess.run(['git', 'show', 'origin/research/n2-near-duplicate:research/n2_near_duplicate/n2b_cards_primary.csv'], capture_output=True, text=True, cwd=HERE).stdout
ref = pd.read_csv(__import__('io').StringIO(ref))
chk = set(zip(ref.set, ref.name)) == set(zip(o.set[has], o.name[has]))
print('pairs', int(np.triu(ok | ok.T).sum()), 'cards', int(has.sum()), 'matches n2b_cards_primary.csv card set:', chk)
d = pd.read_csv(HERE / 'data/da1_cards.csv.gz')
d['raw'] = d.gih_wins / d.gih_games * 100
d['deck'] = d.dadj_sum / d.dadj_n * 100
d['player'] = np.where(d.padj_n > 0, d.padj_sum / d.padj_n.where(d.padj_n > 0, np.nan) * 100, np.nan)
d['colour'] = np.where(d.cadj_n > 0, d.cadj_sum / d.cadj_n.where(d.cadj_n > 0, np.nan) * 100, np.nan)
d = o[['set', 'name', 'actual_gih', 'rarity_ord']].merge(d, left_on=['set', 'name'], right_on=['set', 'card_name'], how='left')
assert len(d) == len(o) and d.deck.notna().all()
V = ['raw', 'deck', 'player', 'colour']
for k in V:
    d[k + '_c'] = d[k] - d.groupby('set')[k].transform('mean')
ii, jj = np.nonzero(np.triu(ok | ok.T))
res = {'n_pairs': int(len(ii)), 'n_cards': int(has.sum()), 'matches_n2b_card_set': bool(chk)}
pairs = pd.DataFrame({'a': d.set[ii].to_numpy() + '|' + d.name[ii].to_numpy(), 'b': d.set[jj].to_numpy() + '|' + d.name[jj].to_numpy()})
for k in V:
    diff = np.abs(d[k + '_c'].to_numpy()[ii] - d[k + '_c'].to_numpy()[jj]); pairs[k] = diff
    res[f'mean_abs_pair_diff_{k}'] = float(np.nanmean(diff)); res[f'n_{k}'] = int(np.isfinite(diff).sum())
    # same pairs, restricted to pairs with all four defined (comparable base)
allok = np.all([np.isfinite(pairs[k]) for k in V], axis=0)
res['n_pairs_all_four'] = int(allok.sum())
for k in V:
    res[f'mean_abs_pair_diff_{k}_allfour'] = float(pairs[k][allok].mean())
sdw = {k: float(d[k + '_c'].std()) for k in V}
for k in V:
    res[f'mean_abs_pair_diff_{k}_over_sd'] = res[f'mean_abs_pair_diff_{k}'] / sdw[k]
rng = np.random.default_rng(20261027); cats = np.array(cat, dtype=object); sets = A('set')
rb = {k: [] for k in V}
for _ in range(200):
    for i0, j0 in zip(ii, jj):
        cand = np.flatnonzero((cats == cats[j0]) & (sets != sets[i0]))
        j1 = rng.choice(cand)
        for k in V:
            rb[k].append(abs(d[k + '_c'].iat[i0] - d[k + '_c'].iat[j1]))
for k in V:
    res[f'random_same_category_pair_diff_{k}'] = float(np.nanmean(rb[k]))
    res[f'pair_over_random_{k}'] = res[f'mean_abs_pair_diff_{k}'] / res[f'random_same_category_pair_diff_{k}']
res['pairs_deck_lower_than_raw'] = int((pairs.deck < pairs.raw).sum())
# between / within variance
def bw(k):
    g = d.groupby('set')[k]
    means = g.mean(); w = float(((d[k] - g.transform('mean')) ** 2).mean()); b = float(means.var(ddof=0))
    return {'between_var': b, 'within_var': w, 'between_share': b / (b + w), 'sd_set_means': float(means.std(ddof=0)), 'total_var': float(d[k].var(ddof=0))}
res['variance'] = {k: bw(k) for k in ['raw', 'deck']}
res['variance_player_colour_sets'] = {k: bw(k) for k in ['player', 'colour']} if False else None
# three named cards
tab = []
for key in ['DMU|Shore Up', 'BLB|Shore Up', 'TLA|Octopus Form']:
    r = d[(d.set + '|' + d.name) == key].iloc[0]
    tab.append({'card': key, 'games': int(r.gih_games), 'raw': r.raw, 'deck': r.deck, 'player': r.player, 'colour': r.colour,
                'raw_c': r.raw_c, 'deck_c': r.deck_c, 'player_c': r.player_c, 'colour_c': r.colour_c})
res['named'] = tab
res['named_pair_diffs'] = {}
for a, b in [('DMU|Shore Up', 'BLB|Shore Up'), ('DMU|Shore Up', 'TLA|Octopus Form'), ('BLB|Shore Up', 'TLA|Octopus Form')]:
    ra = d[(d.set + '|' + d.name) == a].iloc[0]; rb = d[(d.set + '|' + d.name) == b].iloc[0]
    res['named_pair_diffs'][f'{a} vs {b}'] = {k: float(abs(ra[k + '_c'] - rb[k + '_c'])) if np.isfinite(ra[k + '_c'] - rb[k + '_c']) else None for k in V}
    res['named_pair_diffs'][f'{a} vs {b}']['in_n2b_primary'] = bool(((pairs.a == a) & (pairs.b == b)).any() or ((pairs.a == b) & (pairs.b == a)).any())
# corr of adjustments across all cards
res['corr_raw_c_vs_deck_c'] = float(d.raw_c.corr(d.deck_c)); res['corr_raw_c_vs_colour_c'] = float(d.raw_c.corr(d.colour_c)); res['corr_raw_c_vs_player_c'] = float(d.raw_c.corr(d.player_c))
res['sd_within_set'] = {k: float(d[k + '_c'].std()) for k in V}
json.dump(res, open(HERE / 'result_A.json', 'w'), indent=1, default=float)
pairs.assign(**{k: pairs[k].round(3) for k in V}).to_csv(HERE / 'pairs_A.csv', index=False)
print(json.dumps(res, indent=1, default=float))
