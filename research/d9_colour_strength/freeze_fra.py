"""Freeze FRA colour-pair strength predictions (D_B5 and the current formula F0) before any FRA outcome exists.

  python3 research/d9_colour_strength/freeze_fra.py --fra <pages>/data/target.json.gz

D_B5 = deck model F1-F6 (research/deck_model) computed from B5 card predictions, ridge alpha 3 fitted on all 26 sets.
F0_A = mean production card prediction of the pair's commons and uncommons (the current site formula).
FRA card predictions come from the frozen file research/c5_atomic_effects/fra_frozen_predictions.csv (pred_A, pred_B5).
"""
import argparse, gzip, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/deck_model'))
sys.path.insert(0, str(ROOT / 'research/production_c3'))
import deck_model as dm  # noqa: E402
import export_gih_c3_28set as e  # noqa: E402

RAR = {'common': 0, 'uncommon': 1, 'rare': 2, 'mythic': 3}

ap = argparse.ArgumentParser()
ap.add_argument('--fra', type=Path, required=True)
a = ap.parse_args()

pool, base, cols = e.training()
fra, f = e.fra_frame(a.fra, base, cols, pool)
frz = pd.read_csv(ROOT / 'research/c5_atomic_effects/fra_frozen_predictions.csv').set_index('id')
d = pd.DataFrame({'set': 'FRA', 'name': [c['name'] for c in fra], 'id': [c['id'] for c in fra],
                  'colors': [''.join(x for x in dm.COLS if x in c['colors']) for c in fra],
                  'rarity_ord': [RAR.get(c['rarity'], -1) for c in fra], 'type_line': [c['type_line'] for c in fra]})
for k in ['type_land', 'type_creature', 'mv', 'kw_flying', 'kw_menace', 'llm_removal']:
    d[k] = f[k].to_numpy()
d = d[(d['rarity_ord'] >= 0) & ~d['type_line'].str.contains('Basic')].reset_index(drop=True)
n = d.groupby('rarity_ord')['name'].transform('count')
d['w'] = d['rarity_ord'].map(dm.RARITY_PACK) / n


def feats(pred_col):
    x = d.assign(pred=d['id'].map(frz[pred_col]).to_numpy())
    assert x['pred'].notna().all()
    return dm.features(x)


fb5 = feats('pred_B5')
fa = feats('pred_A')
t = pd.read_csv(HERE / 'pair_table.csv')
mu, sd = t[dm.FEATS].mean(), t[dm.FEATS].std(ddof=0).replace(0, 1)
X = ((t[dm.FEATS] - mu) / sd).values
b = np.linalg.solve(X.T @ X + dm.ALPHA * np.eye(len(dm.FEATS)), X.T @ t['y'].values)
out = pd.DataFrame({'pair': fb5['pair'], 'pred_D_B5': ((fb5[dm.FEATS] - mu) / sd).values @ b,
                    'F0_A': fa['F0'].values, 'F0_B5': fb5['F0'].values})
out['rank_D_B5'] = out['pred_D_B5'].rank(ascending=False).astype(int)
out['rank_F0_A'] = out['F0_A'].rank(ascending=False).astype(int)
out.round(5).to_csv(HERE / 'fra_frozen_pairs.csv', index=False)
meta = {'rule': 'Pair strength on FRA (indicative, one set): D_B5 vs F0_A (current site formula) on the centred 28-day pair win rate '
                '(Premier Draft, non-splash two-colour decks, as research/deck_pair): within-set Spearman over 10 pairs and MAE of '
                'scaled predictions (scale fitted on the 26 training sets). Reported, not a decision rule.',
        'coef_std_units': dict(zip(dm.FEATS, b.round(4).tolist())),
        'sha256': hashlib.sha256((HERE / 'fra_frozen_pairs.csv').read_bytes()).hexdigest()}
json.dump(meta, open(HERE / 'fra_frozen_pairs.json', 'w'), indent=1)
print(out.to_string(index=False)); print(meta['sha256'])
