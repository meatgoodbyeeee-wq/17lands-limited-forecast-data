#!/usr/bin/env python3
"""Freeze the FRA B10 80% range (see PLAN.md).  python3 freeze_range.py --fra <pages>/data/target.json.gz"""
import argparse, gzip, hashlib, json, sys, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; R = HERE.parents[0]
sys.path.insert(0, str(R / 'c9_power_questions')); sys.path.insert(0, str(R / 'gih_llm_extract'))
import c9  # noqa
e = c9.e
VERSION = 'gih-b10-28set-20260929'
ap = argparse.ArgumentParser(); ap.add_argument('--fra', type=Path, required=True); a = ap.parse_args()
pred = pd.read_csv(R / 'c9_power_questions/fra_frozen_predictions.csv')
cards = json.loads(gzip.open(a.fra, 'rt', encoding='utf-8').read())['cards']
assert set(pred['id']) == {c['id'] for c in cards}, 'card list differs from the frozen predictions'
tmp = HERE / 'tmp'; tmp.mkdir(exist_ok=True)
adopted = tmp / 'adopted_fra_b10.json.gz'
with gzip.open(adopted, 'wt', encoding='utf-8') as fh:
    json.dump({'version': VERSION, 'cards': [{'id': i, 'name': n, 'gih': float(p) * 100} for i, n, p in zip(pred['id'], pred['name'], pred['pred_B10'])]}, fh)
pool, base, cols = c9.load_pool()
pool_t = pool[['set', 'name', 'type_line']].drop_duplicates(['set', 'name'])
o = pd.read_csv(R / 'c9_power_questions/oof_B10.csv.gz').merge(pool_t, on=['set', 'name'], how='left', validate='one_to_one')
assert o['type_line'].notna().all()
oof = tmp / 'oof_b10_for_range.csv.gz'
o[['set', 'name', 'rarity_ord', 'type_line', 'actual_gih', 'pred']].to_csv(oof, index=False, compression='gzip')
e.OOF = oof
out = HERE / 'fra_b10_range.json'
e.cmd_range(argparse.Namespace(fra=a.fra, set='FRA', c3=None, version=VERSION, adopted=adopted, out=out))
meta = {'rule': 'FRA B10 M5 range frozen from fra_frozen_predictions.csv pred_B10; reported-only coverage on FRA 28-day GIH WR (PLAN.md)',
        'sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'predictions_sha256': hashlib.sha256((R / 'c9_power_questions/fra_frozen_predictions.csv').read_bytes()).hexdigest()}
json.dump(meta, open(HERE / 'fra_b10_range.meta.json', 'w'), indent=1); print(meta)
