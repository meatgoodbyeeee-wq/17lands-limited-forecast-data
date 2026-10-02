"""Freeze FRA predictions of arm B (baseline + C3 + C4) next to production A, before any FRA outcome exists.

  python3 freeze_fra.py --fra <pages>/data/target.json.gz
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c4  # noqa: E402
e = c4.e

ap = argparse.ArgumentParser()
ap.add_argument('--fra', type=Path, required=True)
a = ap.parse_args()
pool, base, cols, _ = c4.load_pool()
fra, f = e.fra_frame(a.fra, base, cols, pool)
c4t = pd.read_csv(HERE / 'c4_features.csv.gz').set_index('key')
keys = [f"FRA|{c['id']}" for c in fra]
assert all(k in c4t.index for k in keys)
for c in c4.C4_NUM + c4.C4_ROLE:
    f[c] = c4t.loc[keys, c].to_numpy(dtype=float)
nums_a, nums_b = base + cols, base + cols + c4.C4_NUM + c4.C4_ROLE
_, _, _, pa = e.predict(pool, f, nums_a)
_, _, _, pb = e.predict(pool, f, nums_b)
out = pd.DataFrame({'id': [c['id'] for c in fra], 'name': [c['name'] for c in fra], 'pred_A': pa, 'pred_B': pb})
out.to_csv(HERE / 'fra_frozen_predictions.csv', index=False)
meta = {'rule': 'Rule F: B (baseline+C3+C4) vs A (production gih-c3-28set-20260929); score on FRA 28-day GIH WR, cards with >= 500 GIH games: MAE, within-set Spearman',
        'seeds': list(c4.SEEDS), 'sha256': hashlib.sha256((HERE / 'fra_frozen_predictions.csv').read_bytes()).hexdigest()}
json.dump(meta, open(HERE / 'fra_frozen_predictions.json', 'w'), indent=1)
print(meta, float(np.corrcoef(pa, pb)[0, 1]), float(np.abs(pa - pb).mean() * 100))
