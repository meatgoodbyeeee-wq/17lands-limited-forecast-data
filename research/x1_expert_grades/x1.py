import glob, re, json, numpy as np, pandas as pd, io, subprocess, gzip
from pathlib import Path
from scipy.stats import spearmanr
H = Path(__file__).resolve().parent; R = H.parents[1]
def nm(s): return re.sub(r'[^a-z0-9]', '', str(s).split('//')[0].lower())
o = pd.read_csv(R/'research/c9_power_questions/oof_B10.csv.gz')
fr = pd.read_csv(R/'research/c9_power_questions/fra_frozen_predictions.csv')
a = pd.read_csv(H/'fra_actual_public_20261017.csv'); fr = fr.merge(a, on='name'); fr = fr[fr.gih_games >= 500]
rar = {c['name']: c['rarity'] for c in json.load(gzip.open('/home/claude/pageswt/data/target.json.gz'))['cards']}
fr = pd.DataFrame({'set': 'FRA', 'name': fr.name, 'rarity_ord': fr.name.map(rar).map({'common': 0, 'uncommon': 1, 'rare': 2, 'mythic': 3}),
                   'actual_gih': fr.actual_gih, 'pred': fr.pred_B10})
d = pd.concat([o, fr], ignore_index=True); d['k'] = d.name.map(nm)
import sys
ARM = sys.argv[1] if len(sys.argv) > 1 else 'primary'
REL = json.load(open(H/'release_dates.json'))
G = {}
for f in sorted(glob.glob(str(H/'grades/*.csv'))):
    s = Path(f).stem; g = pd.read_csv(f); g = g[pd.to_numeric(g.rating, errors='coerce').notna()]
    if ARM == 'primary': g = g[g.published.astype(str).str[:10] <= REL[s]]
    G[s] = g.assign(k=g.name.map(nm)).drop_duplicates('k').set_index('k').rating.astype(float)
d = d[d.set.isin(G)].copy()
d['grade'] = [G[s].get(k, np.nan) for s, k in zip(d.set, d.k)]
d['y'] = (d.actual_gih - d.groupby('set').actual_gih.transform('mean'))*100
d['p'] = (d.pred - d.groupby('set').pred.transform('mean'))*100
d['g'] = d.grade - d.groupby('set').grade.transform('mean')
sets = sorted(G); past = [s for s in sets if s != 'FRA']
def fit(tr):
    t = d[d.set.isin(tr) & d.grade.notna()]; X = np.c_[np.ones(len(t)), t.p, t.g]
    return np.linalg.lstsq(X, t.y, rcond=None)[0]
def apply(s, c):
    t = d[d.set == s]; yh = np.where(t.grade.notna(), c[0] + c[1]*t.p + c[2]*t.g.fillna(0), t.p)
    return t.pred*100 + (yh - t.p)   # back on the raw-GIH scale (pp)
rows = []; d['x1'] = np.nan
for s in sets:
    c = fit([x for x in past if x != s]); d.loc[d.set == s, 'x1'] = apply(s, c).values
    t = d[d.set == s]
    rows.append({'set': s, 'n': len(t), 'graded': int(t.grade.notna().sum()), 'coef': c.round(3).tolist(),
                 'mae_B10': float((t.pred*100 - t.actual_gih*100).abs().mean()), 'mae_X1': float((t.x1 - t.actual_gih*100).abs().mean()),
                 'sp_B10': spearmanr(t.pred, t.actual_gih)[0], 'sp_X1': spearmanr(t.x1, t.actual_gih)[0],
                 'rho_grade_resid': spearmanr(t.grade, t.y - t.p, nan_policy='omit')[0]})
r = pd.DataFrame(rows); print(r.round(3).to_string())
P = d[d.set.isin(past)]
summ = {'past_sets': past, 'pooled_mae_B10': float((P.pred*100 - P.actual_gih*100).abs().mean()), 'pooled_mae_X1': float((P.x1 - P.actual_gih*100).abs().mean()),
        'mean_sp_B10': float(r[r.set != 'FRA'].sp_B10.mean()), 'mean_sp_X1': float(r[r.set != 'FRA'].sp_X1.mean()),
        'sets_improved': int((r[r.set != 'FRA'].mae_X1 < r[r.set != 'FRA'].mae_B10).sum())}
summ['pass'] = bool(summ['pooled_mae_B10'] - summ['pooled_mae_X1'] >= 0.05 and summ['mean_sp_X1'] > summ['mean_sp_B10'] and summ['sets_improved'] >= np.ceil(len(past)*2/3))
for rk, lab in enumerate('CURM'):
    q = P[P.rarity_ord == rk]; summ[f'mae_{lab}'] = [float((q.pred*100 - q.actual_gih*100).abs().mean()), float((q.x1 - q.actual_gih*100).abs().mean())]
top = P[P.groupby('set').actual_gih.rank(pct=True) > .9]
summ['top10_under'] = [float((top.actual_gih*100 - top.pred*100).mean()), float((top.actual_gih*100 - top.x1).mean())]
print(json.dumps(summ, indent=1))
r.to_csv(H/f'per_set_{ARM}.csv', index=False); json.dump(summ, open(H/f'result_{ARM}.json', 'w'), indent=1)
d[['set', 'name', 'rarity_ord', 'actual_gih', 'pred', 'grade', 'x1']].to_csv(H/f'cards_x1_{ARM}.csv.gz', index=False)
