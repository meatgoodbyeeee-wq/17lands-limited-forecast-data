"""Why do experts miss? 13 sets with pre-release expert grades (MTGAZone 0-5). Expert-implied prediction = pooled linear fit of
within-set actual (pp) on within-set grade z (fit on other sets, LOSO). Expert residual = actual - expert-implied."""
import runpy, sys, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
G = Path(__file__).resolve().parents[1]/'g3_expert_grade'
sys.argv = ['x']; ns = runpy.run_path(str(G/'build.py')); o, k2 = ns['o'].copy(), ns['k2']
o = o[o.grade.notna()].copy()
o['txt'] = [str(k2[k].btext).lower() for k in o.key]; o['typ'] = [str(k2[k].type_line).lower() for k in o.key]
o['col'] = [str(k2[k].colors) for k in o.key]; o['mv'] = [pd.to_numeric(k2[k].mv, errors='coerce') for k in o.key]
o['y'] = (o.actual_gih - o.groupby('set').actual_gih.transform('mean'))*100
o['p'] = (o.pred - o.groupby('set').pred.transform('mean'))*100; o['bres'] = o.y - o.p
o['gz'] = (o.grade - o.groupby('set').grade.transform('mean'))/o.groupby('set').grade.transform('std')
o['e'] = np.nan
for s in o.set.unique():
    tr = o.set != s; b = np.polyfit(o.gz[tr], o.y[tr], 1); o.loc[~tr, 'e'] = np.polyval(b, o.gz[~tr])
o['eres'] = o.y - o.e
print('sets', o.set.nunique(), 'cards', len(o))
print('MAE expert-implied %.3f | B10 %.3f | corr(expert residual, B10 residual) %.3f' % (o.eres.abs().mean(), o.bres.abs().mean(), np.corrcoef(o.eres, o.bres)[0, 1]))
# 1) decomposition of expert squared error: set x colour mean, set x rarity, card-specific
o['mono'] = o.col.str.len() == 1; o['c1'] = np.where(o.mono, o.col, np.where(o.col.str.len() == 0, 'C', 'M'))
tot = (o.eres**2).sum()
for name, keys in [('colour within set', ['set', 'c1']), ('rarity within set', ['set', 'rarity_ord']), ('colour x rarity within set', ['set', 'c1', 'rarity_ord'])]:
    m = o.groupby(keys).eres.transform('mean'); print(f'share of expert sq. error explained by {name}: {1 - ((o.eres - m)**2).sum()/tot:.3f}')
# 2) by grade level: are experts compressed / biased by grade?
o['gb'] = pd.cut(o.grade, [-.1, 1, 2, 2.5, 3, 3.5, 5])
print(o.groupby('gb', observed=True).agg(n=('y', 'size'), actual=('y', 'mean'), expert_implied=('e', 'mean'), expert_res=('eres', 'mean'), b10_res=('bres', 'mean')).round(2))
# 3) by rarity and by card type
o['kind'] = np.select([o.typ.str.contains('creature'), o.typ.str.contains('instant|sorcery'), o.typ.str.contains('land')], ['creature', 'spell', 'land'], 'other')
print(o.groupby(['rarity_ord']).agg(n=('y', 'size'), expert_res_abs=('eres', lambda x: x.abs().mean()), b10_res_abs=('bres', lambda x: x.abs().mean())).round(2))
print(o.groupby(['kind']).agg(n=('y', 'size'), expert_res=('eres', 'mean'), b10_res=('bres', 'mean')).round(2))
# creatures by MV: experts vs actual
c = o[o.kind == 'creature']; c['mvb'] = c.mv.clip(upper=6)
print(c.groupby('mvb').agg(n=('y', 'size'), expert_res=('eres', 'mean'), b10_res=('bres', 'mean')).round(2))
# 4) colour-level misses per set: how big is the colour-strength misjudgement?
cm = o[o.mono].groupby(['set', 'c1']).agg(eres=('eres', 'mean'), n=('y', 'size')).reset_index()
print('per-set colour mean expert residual: SD %.2f pp; largest:' % cm.eres.std()); print(cm.reindex(cm.eres.abs().sort_values(ascending=False).index).head(8).round(2).to_string(index=False))
o.to_csv('expert_resid.csv.gz', index=False)
