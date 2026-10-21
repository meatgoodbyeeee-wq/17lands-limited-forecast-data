"""Independent recomputation of M1's key numbers (does not import m1.py; different code paths).
python3 -I check_m1.py   -> prints values to compare with result.json / log.txt"""
import os, re, json, glob, unicodedata
from collections import defaultdict
import numpy as np, pandas as pd
from scipy.stats import rankdata
HERE = os.path.dirname(os.path.abspath(__file__))
def key(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
def spearman(x, y): return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
o = pd.read_csv(HERE + '/../c9_power_questions/oof_B10.csv.gz'); o = o[o['set'] == 'MSH']
act = {key(n): v for n, v in zip(o['name'], o['actual_gih'])}; prd = {key(n): v for n, v in zip(o['name'], o['pred'])}
am, pm = np.mean(list(act.values())), np.mean(list(prd.values()))
def tally(mode):
    wins, n, games, slow = defaultdict(int), defaultdict(int), 0, 0
    for f in glob.glob(f'{HERE}/m1_games/{mode}/job*.json'):
        for g in json.load(open(f)):
            games += 1; slow += bool(g['slow'])
            if g['slow'] or g['winner'] is None: continue
            for deck, cards in g['draws'].items():
                for c in cards:
                    k = key(c)
                    if k in act: n[k] += 1; wins[k] += (deck == g['winner'])
    return wins, n, games, slow
T = {m: tally(m) for m in ('normal', 'hybrid')}
common = sorted(k for k in act if all(T[m][1].get(k, 0) >= 100 for m in T))
print('games', {m: T[m][2] for m in T}, 'slow', {m: T[m][3] for m in T}, 'common cards', len(common))
a = np.array([(act[k] - am) * 100 for k in common]); p = np.array([(prd[k] - pm) * 100 for k in common]); res = a - p
E = {}
for m in T:
    g = np.array([T[m][0][k] / T[m][1][k] for k in common]); E[m] = (g - g.mean()) * 100
def loo_mae(X):  # hat-matrix shortcut
    X = np.c_[np.ones(len(a)), X]; H = X @ np.linalg.pinv(X.T @ X) @ X.T; r = a - H @ a
    return float(np.mean(np.abs(r / (1 - np.diag(H)))))
print('LOO MAE p-only %.3f' % loo_mae(p[:, None]))
for m in T:
    print(f'[{m}] rho(e,a) {spearman(E[m], a):+.3f}  rho(e,res) {spearman(E[m], res):+.3f}  LOO MAE p+e {loo_mae(np.c_[p, E[m]]):.3f}')
rng = np.random.default_rng(11); n = len(a); d = []
for _ in range(5000):
    ix = rng.integers(0, n, n); d.append(spearman(E['hybrid'][ix], a[ix]) - spearman(E['normal'][ix], a[ix]))
print('delta rho H-C %+.3f  CI [%+.3f, %+.3f] (5000, seed 11)' % (spearman(E['hybrid'], a) - spearman(E['normal'], a), *np.percentile(d, [2.5, 97.5])))
