"""K1 analysis. python3 -I k1.py <k1_games_dir>"""
import sys, json, re, glob, unicodedata, random, math
import numpy as np, pandas as pd
from scipy import stats
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
G = []
for f in sorted(glob.glob(sys.argv[1] + '/job?.json')): G += json.load(open(f))
print('games', len(G), 'no winner', sum(g['winner'] is None for g in G))
o = pd.read_csv('../c9_power_questions/oof_B10.csv.gz'); o = o[o.set == 'MSH'].copy()
o['a'] = (o.actual_gih - o.actual_gih.mean()) * 100; o['p'] = (o.pred - o.pred.mean()) * 100; o['res'] = o.a - o.p
o['k'] = o.name.map(norm)
# obs: (card key, win) per (deck, game)
obs = []
for gi, g in enumerate(G):
    if g['winner'] is None: continue
    for dk, cards in g['draws'].items():
        for c in cards: obs.append((norm(c), int(g['winner'] == dk), gi))
ob = pd.DataFrame(obs, columns=['k', 'w', 'gi']); ob = ob[ob.k.isin(set(o.k))]
print('card-draw obs', len(ob))
cnt = ob.groupby('k').w.agg(['size', 'mean']).rename(columns={'size': 'n', 'mean': 'gih'})
elig = cnt[cnt.n >= 150]; print('eligible', len(elig), 'excluded (<150)', len(cnt) - len(elig), 'of MSH cards', len(o))
m = elig.mean().gih if False else elig.gih.mean()
elig = elig.assign(e=(elig.gih - m) * 100)
d = o.merge(elig, left_on='k', right_index=True)
d = d.assign(e_c=d.e - d.e.mean())
# (1) split-half reliability
rng = random.Random(1); gis = sorted(ob.gi.unique()); rs = []
for _ in range(20):
    half = set(rng.sample(gis, len(gis) // 2)); A = ob[ob.gi.isin(half)].groupby('k').w.mean(); Bh = ob[~ob.gi.isin(half)].groupby('k').w.mean()
    j = A.index.intersection(Bh.index).intersection(d.k); r = stats.spearmanr(A[j], Bh[j])[0]; rs.append(2 * r / (1 + r))
rel = float(np.mean(rs)); print('split-half Spearman-Brown', round(rel, 3))
# (2)
r1 = stats.spearmanr(d.e, d.a); r2 = stats.spearmanr(d.e, d.res)
print('spearman(e,a) %.3f p=%.3g n=%d' % (r1[0], r1[1], len(d)))
print('spearman(e,res) %.3f p_one_sided=%.3g' % (r2[0], r2[1] / 2 if r2[0] > 0 else 1 - r2[1] / 2))
# (3) AA
d['rank_e'] = d.e.rank(ascending=False)
aa = d[d.name == 'Avengers Assemble!']
if len(aa):
    x = aa.iloc[0]; print('AA e %.2f rank %d/%d a %.2f p %.2f res %.2f n_draws %d' % (x.e, x.rank_e, len(d), x.a, x.p, x.res, x.n))
else: print('AA not eligible', cnt.loc['avengersassemble'] if 'avengersassemble' in cnt.index else 'no draws')
# (4) LOO MAE
def loo(cols):
    X = np.c_[np.ones(len(d)), d[cols].values]; y = d.a.values; err = []
    for i in range(len(d)):
        t = np.arange(len(d)) != i; b = np.linalg.lstsq(X[t], y[t], rcond=None)[0]; err.append(abs(y[i] - X[i] @ b))
    return float(np.mean(err))
m1, m2 = loo(['p']), loo(['p', 'e']); print('LOO MAE p-only %.3f  p+e %.3f' % (m1, m2))
b = np.linalg.lstsq(np.c_[np.ones(len(d)), d.p, d.e], d.a, rcond=None)[0]; print('coef a~p+e', b.round(3))
# (5)
d['gap'] = d.e_c - d.res
t = d.sort_values('gap'); cols = ['name', 'n', 'e', 'a', 'p', 'res']
print('--- e much lower than res (engine says weaker)'); print(t[cols].head(10).round(1).to_string(index=False))
print('--- e much higher than res (engine says stronger)'); print(t[cols].tail(10).round(1).to_string(index=False))
sup = bool(r2[0] > 0 and (r2[1] / 2 < 0.05) and m2 < m1); print('RULE K1 supported:', sup)
json.dump(dict(games=len(G), eligible=len(elig), reliability=rel, rho_e_a=r1[0], p_e_a=r1[1], rho_e_res=r2[0], p_e_res=r2[1], mae_p=m1, mae_pe=m2, supported=sup), open('result.json', 'w'), indent=1)
