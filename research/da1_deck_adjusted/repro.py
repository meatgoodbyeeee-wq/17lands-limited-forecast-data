"""Reproduce oof_B10 for one set with the B10 code path (time + max abs diff)."""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'c9_power_questions'))
import c9
from c9 import c5, e
S = sys.argv[1] if len(sys.argv) > 1 else 'HOB'
pool, base, cols = c9.load_pool()
b5 = c5.arm_nums('B5', base, cols)
nums = b5 + c9.MEAN + c9.SD + c9.SUM
te = (pool['set'] == S).to_numpy()
t0 = time.time(); ps = []
for sd in c9.SEEDS:
    c, t, x = e.parts(pool[~te], pool[te], nums, sd); ps.append(c + 1.25 * (.7 * t + .3 * x - c))
p = np.mean(ps, axis=0)
o = pd.read_csv(HERE.parent / 'c9_power_questions/oof_B10.csv.gz'); o = o[o['set'] == S]
assert (o['name'].to_numpy() == pool.loc[te, 'name'].to_numpy()).all()
print(S, len(o), 'max abs diff', np.abs(p - o['pred'].to_numpy()).max(), 'sec', time.time() - t0, 'nfeat', len(nums))
