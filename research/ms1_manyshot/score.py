"""python3 score.py <SETDIR>  -> prints and writes <SETDIR>/score.json"""
import sys, json, glob, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
D = Path(sys.argv[1]); k = pd.read_csv(D/'targets_key.csv'); P = []
for f in sorted(D.glob('pass*.json')):
    d = json.load(open(f)); assert len(d) == len(k), f; k[f.stem] = k.tid.map(d); P.append(f.stem)
k['ms'] = k[P].mean(axis=1); k['blend'] = .5*k.pdelta + .5*k.ms
mae = lambda c, s=k: float((s[c]-s.delta).abs().mean())
r = {'n': len(k), 'sp_B10': spearmanr(k.pdelta, k.delta)[0], 'sp_MS': spearmanr(k.ms, k.delta)[0],
     'sp_blend': spearmanr(k.blend, k.delta)[0], 'mae_B10': mae('pdelta'), 'mae_MS': mae('ms'), 'mae_blend': mae('blend'),
     'pass_agree': [spearmanr(k[a], k[b])[0] for i, a in enumerate(P) for b in P[i+1:]]}
rng = np.random.default_rng(0); ds, dm = [], []
for _ in range(4000):
    s = k.iloc[rng.integers(0, len(k), len(k))]
    ds.append(spearmanr(s.ms, s.delta)[0]-spearmanr(s.pdelta, s.delta)[0]); dm.append(mae('pdelta', s)-mae('blend', s))
r['dsp_ci'] = list(np.percentile(ds, [2.5, 50, 97.5])); r['dmae_ci'] = list(np.percentile(dm, [2.5, 50, 97.5]))
t = k.nlargest(10, 'delta'); r['top10_under_B10'] = float((t.delta-t.pdelta).mean()); r['top10_under_blend'] = float((t.delta-t.blend).mean())
r['pass'] = bool(r['sp_MS'] > r['sp_B10'] and r['mae_blend'] < r['mae_B10'])
json.dump(r, open(D/'score.json', 'w'), indent=1); k.to_csv(D/'scored.csv', index=False)
print(D.name, json.dumps({a: (round(b, 3) if isinstance(b, float) else b) for a, b in r.items()}))
