"""Freeze FRA predictions of B5 (baseline+C3+C4+C5) next to A and B, before any FRA outcome exists.

  python3 freeze_fra.py --fra <pages>/data/target.json.gz
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c5  # noqa: E402
e = c5.e

ap = argparse.ArgumentParser()
ap.add_argument('--fra', type=Path, required=True)
a = ap.parse_args()
pool, base, cols, _ = c5.load_pool()
fra, f = e.fra_frame(a.fra, base, cols, pool)
keys = [f"FRA|{c['id']}" for c in fra]
for src, names in ((c5.C4DIR / 'c4_features.csv.gz', c5.C4_NUM + c5.C4_ROLE), (HERE / 'c5_features.csv.gz', c5.TAGC + c5.SCALE + c5.CNT)):
    t = pd.read_csv(src).set_index('key')
    assert all(k in t.index for k in keys)
    for c in names:
        f[c] = t.loc[keys, c].to_numpy(dtype=float)
nums_a = base + cols
nums_b = base + cols + c5.C4_NUM + c5.C4_ROLE
nums_5 = c5.arm_nums('B5', base, cols)
_, _, _, pa = e.predict(pool, f, nums_a)
_, _, _, pb = e.predict(pool, f, nums_b)
_, _, _, p5 = e.predict(pool, f, nums_5)
out = pd.DataFrame({'id': [c['id'] for c in fra], 'name': [c['name'] for c in fra], 'pred_A': pa, 'pred_B': pb, 'pred_B5': p5})
out.to_csv(HERE / 'fra_frozen_predictions.csv', index=False)
meta = {'rule': 'Rule F5: B5 (baseline+C3+C4+C5) vs B (C4) vs A (production gih-c3-28set-20260929); score on FRA 28-day GIH WR, cards with >= 500 GIH games: MAE, within-set Spearman',
        'seeds': list(c5.SEEDS), 'sha256': hashlib.sha256((HERE / 'fra_frozen_predictions.csv').read_bytes()).hexdigest()}
json.dump(meta, open(HERE / 'fra_frozen_predictions.json', 'w'), indent=1)
print(meta, float(np.corrcoef(pa, p5)[0, 1]), float(np.abs(pa - p5).mean() * 100), float(np.abs(pb - p5).mean() * 100))
