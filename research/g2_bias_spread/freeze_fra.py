"""Freeze FRA predictions of arm S (B10 spread by slope b fitted on all 28 sets' OOF) before any FRA outcome is used."""
import hashlib, json, numpy as np, pandas as pd
d = pd.read_csv('research/g2_bias_spread/oof_g2.csv.gz')
b = float(np.polyfit(d.p, d.a, 1)[0])
f = pd.read_csv('research/c9_power_questions/fra_frozen_predictions.csv')
m = f.pred_B10.mean()
f['pred_B10S'] = m + b * (f.pred_B10 - m)
f.to_csv('research/g2_bias_spread/fra_frozen_predictions.csv', index=False)
sha = hashlib.sha256(open('research/g2_bias_spread/fra_frozen_predictions.csv', 'rb').read()).hexdigest()
meta = dict(rule='Rule F22 arm S: pred_B10S = set mean + b*(pred_B10 - set mean) vs pred_B10; score on FRA 28-day GIH WR, cards with >= 500 GIH games: MAE, within-set Spearman (unchanged by construction), predicted-top-10% a-p (indicative, one set)', b=b, sha256=sha)
json.dump(meta, open('research/g2_bias_spread/fra_frozen_predictions.json', 'w'), indent=1); print(meta)
