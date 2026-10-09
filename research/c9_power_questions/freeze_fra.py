"""Freeze FRA predictions of B10 (B5 + C9 power questions) next to A, B, B5, before any FRA outcome exists.

  python3 freeze_fra.py --fra <pages>/data/target.json.gz
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c9  # noqa: E402
c5, e = c9.c5, c9.e

ap = argparse.ArgumentParser()
ap.add_argument('--fra', type=Path, required=True)
a = ap.parse_args()
pool, base, cols = c9.load_pool()
fra, f = e.fra_frame(a.fra, base, cols, pool)
keys = [f"FRA|{c['id']}" for c in fra]
for src, names in ((c5.C4DIR / 'c4_features.csv.gz', c5.C4_NUM + c5.C4_ROLE), (c5.HERE / 'c5_features.csv.gz', c5.TAGC + c5.SCALE + c5.CNT),
                   (HERE / 'c9_features.csv.gz', c9.MEAN + c9.SD + c9.SUM)):
    t = pd.read_csv(src).set_index('key')
    assert all(k in t.index for k in keys)
    for c in names:
        f[c] = t.loc[keys, c].to_numpy(dtype=float)
nums = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
_, _, _, p10 = e.predict(pool, f, nums)
old = pd.read_csv(ROOT := c5.ROOT / 'research/c5_atomic_effects/fra_frozen_predictions.csv').set_index('id')
out = pd.DataFrame({'id': [c['id'] for c in fra], 'name': [c['name'] for c in fra]})
out['pred_A'] = out['id'].map(old['pred_A']); out['pred_B'] = out['id'].map(old['pred_B']); out['pred_B5'] = out['id'].map(old['pred_B5'])
out['pred_B10'] = p10
assert out.notna().all().all()
out.to_csv(HERE / 'fra_frozen_predictions.csv', index=False)
meta = {'rule': 'Rule F10: B10 (B5 + C9 power questions x3 passes) vs B5, B, A; score on FRA 28-day GIH WR, cards with >= 500 GIH games: MAE, within-set Spearman (indicative, one set)',
        'seeds': list(c5.SEEDS), 'sha256': hashlib.sha256((HERE / 'fra_frozen_predictions.csv').read_bytes()).hexdigest()}
json.dump(meta, open(HERE / 'fra_frozen_predictions.json', 'w'), indent=1)
print(meta, float(np.corrcoef(out.pred_B5, p10)[0, 1]), float(np.abs(out.pred_B5 - p10).mean() * 100))
