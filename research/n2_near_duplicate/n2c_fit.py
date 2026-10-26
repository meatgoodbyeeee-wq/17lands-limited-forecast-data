"""N2c: B10 fit leaving out a given list of sets; writes predictions for the held-out sets.
  python3 n2c_fit.py OUT.csv SET1[,SET2]   (leave-out = all listed sets; predicts every listed set)
Same code path as c9.run_arm('B10') (3 seeds, same blend)."""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'c9_power_questions'))
import c9
c5, e = c9.c5, c9.e

def fit(pool, nums, outsets):
    te = pool['set'].isin(outsets).to_numpy(); ps = []
    for sd in c9.SEEDS:
        c, t, x = e.parts(pool[~te], pool[te], nums, sd)
        ps.append(c + 1.25 * (.7 * t + .3 * x - c))
    return pool[te][['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=np.mean(ps, axis=0))

if __name__ == '__main__':
    t0 = time.time()
    pool, base, cols = c9.load_pool()
    b5 = c5.arm_nums('B5', base, cols)
    nums = b5 + c9.MEAN + c9.SD + c9.SUM
    outs = sys.argv[2].split(',')
    fit(pool, nums, outs).to_csv(sys.argv[1], index=False)
    print('done', outs, round(time.time() - t0, 1), 's', flush=True)
