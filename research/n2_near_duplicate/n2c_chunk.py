"""python3 n2c_chunk.py CHUNK NCHUNK OUTDIR : fit B10 without both sets for every pair i with i % NCHUNK == CHUNK."""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import n2c_fit as f
ch, n, out = int(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
pairs = json.load(open(HERE / 'n2c_pairs.json'))
pool, base, cols = f.c9.load_pool()
nums = f.c5.arm_nums('B5', base, cols) + f.c9.MEAN + f.c9.SD + f.c9.SUM
if ch == 0:  # reproduction check: S only excluded must equal oof_B10
    a = f.fit(pool, nums, ['AFR']); o = pd.read_csv(HERE.parent / 'c9_power_questions/oof_B10.csv.gz'); o = o[o.set == 'AFR']
    m = a.merge(o, on=['set', 'name'], suffixes=('', '_o')); d = float(np.abs(m.pred - m.pred_o).max())
    print('REPRO AFR n=%d maxdiff=%g' % (len(m), d), flush=True); open(out / 'repro.txt', 'w').write('%d %g\n' % (len(m), d))
for i, (s, t) in enumerate(pairs):
    if i % n != ch: continue
    t0 = time.time(); f.fit(pool, nums, [s, t]).to_csv(out / f'{s}_{t}.csv', index=False)
    print(s, t, round(time.time() - t0, 1), flush=True)
