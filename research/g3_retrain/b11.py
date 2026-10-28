"""python3 b11.py arm <B11g|B11h> | evaluate"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
H = Path(__file__).resolve().parent; R = H.parents[1]
sys.path.insert(0, str(R/'research/c9_power_questions')); sys.path.insert(0, str(R/'research/c5_atomic_effects'))
sys.argv, _a = ['c9'], sys.argv
import c9; c5 = c9.c5; e = c9.e
sys.argv = _a
G = R/'research/g3_expert_grade'
LESSON = ['BLB','DFT','DSK','EOE','FDN','LCI','MKM','OTJ','SOS','TDM','TLA']
def g3_table():
    rows = []
    for k in sorted((G/'keys_all').glob('*.csv')):
        s = k.stem; key = pd.read_csv(k); d = json.load(open(G/'all'/s/'pass1.json')); assert len(d) == len(key), s
        key['g3'] = key.tid.map(d).astype(float); key['g3_z'] = (key.g3 - key.g3.mean())/key.g3.std(); rows.append(key[['key', 'g3', 'g3_z']])
    return pd.concat(rows)
def run_arm(name):
    pool, base, cols = c9.load_pool(); pool = pool.merge(g3_table(), on='key', how='left'); assert pool.g3.isna().mean() < 0.01
    pool[['g3', 'g3_z']] = pool[['g3', 'g3_z']].fillna(pool.groupby('set').g3.transform('mean')).fillna(0)
    b5 = c5.arm_nums('B5', base, cols)
    nums = (b5 if name == 'B11g' else b5 + c9.MEAN + c9.SD + c9.SUM) + ['g3', 'g3_z']
    pred = np.full(len(pool), np.nan)
    for s in sorted(pool['set'].unique()):
        te = (pool['set'] == s).to_numpy(); ps = []
        for sd in c9.SEEDS:
            c, t, x = e.parts(pool[~te], pool[te], nums, sd); ps.append(c + 1.25*(.7*t + .3*x - c))
        pred[te] = np.mean(ps, axis=0); print(name, s, flush=True)
    pool[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=pred).to_csv(H/f'oof_{name}.csv.gz', index=False, compression='gzip')
def evaluate():
    ref = {'B5': pd.read_csv(R/'research/c5_atomic_effects/oof_B5.csv.gz'), 'B10': pd.read_csv(R/'research/c9_power_questions/oof_B10.csv.gz')}
    for n in ['B11g', 'B11h']:
        if (H/f'oof_{n}.csv.gz').exists(): ref[n] = pd.read_csv(H/f'oof_{n}.csv.gz')
    out = {}
    for grp, ss in [('eval17', None), ('lesson11', LESSON), ('all28', None)]:
        for n, d in ref.items():
            d = d.copy(); d['e'] = (d.pred - d.actual_gih).abs()*100
            sel = d[d.set.isin(LESSON)] if grp == 'lesson11' else d[~d.set.isin(LESSON)] if grp == 'eval17' else d
            per = sel.groupby('set').apply(lambda g: pd.Series({'mae': g.e.mean(), 'sp': spearmanr(g.pred, g.actual_gih)[0],
                       'top_mae': g.nlargest(max(1, len(g)//10), 'actual_gih').e.mean()}))
            out.setdefault(grp, {})[n] = {'mae_pooled': float(sel.e.mean()), 'mae_set_mean': float(per.mae.mean()), 'spearman': float(per.sp.mean()), 'top_decile_mae': float(per.top_mae.mean()),
                                          'sets_better_than_B10': None}
        b10 = ref['B10'].assign(e=lambda d: (d.pred - d.actual_gih).abs()*100)
        for n, d in ref.items():
            if n == 'B10': continue
            d = d.assign(e=(d.pred - d.actual_gih).abs()*100)
            f = (lambda x: x[x.set.isin(LESSON)]) if grp == 'lesson11' else (lambda x: x[~x.set.isin(LESSON)]) if grp == 'eval17' else (lambda x: x)
            a, b = f(d).groupby('set').e.mean(), f(b10).groupby('set').e.mean()
            out[grp][n]['sets_better_than_B10'] = f'{int((a < b).sum())}/{len(a)}'
    g, b = out['eval17'].get('B11g'), out['eval17']['B10']
    if g: out['decision_B11g_ok'] = bool(g['mae_set_mean'] <= b['mae_set_mean'] + 0.02 and g['spearman'] >= b['spearman'] - 0.005)
    json.dump(out, open(H/'result.json', 'w'), indent=1); print(json.dumps(out, indent=1))
if __name__ == '__main__':
    {'arm': lambda: run_arm(sys.argv[2]), 'evaluate': evaluate}[sys.argv[1]]()
