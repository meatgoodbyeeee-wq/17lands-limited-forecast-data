"""F1 analysis (Rule F20). python3 f1.py"""
import json, re
from pathlib import Path
import numpy as np, pandas as pd
H = Path(__file__).resolve().parent; R = H.parent
LINE = re.compile(r'#?([A-Z0-9_]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([\d.]+)\s*\|?\s*(.*)')
sub = pd.read_csv(R / 'h1_judge_reliability/subset.csv')
act = pd.read_csv(R / 'c9_power_questions/oof_B10.csv.gz'); act['c'] = (act.actual_gih - act.groupby('set').actual_gih.transform('mean')) * 100
act['key'] = act.set + '|' + act.name; act = act.set_index('key').c
sim = pd.read_csv(R / 'a3_simulated_p/deck_sim.csv').set_index('name')
rows = []
for r in sub.itertuples():
    p = H / 'out' / f'{r.name}.txt'; m = LINE.match(p.read_text().strip()) if p.exists() else None
    if m and m.group(1) in (str(r.id), r.name):
        rows.append({'name': r.name, 'key': r.key, 'off': float(m.group(2)), 'on': float(m.group(3)), 'p': float(m.group(4)) / 100, 'psim': sim.loc[r.name, 'psim']})
d = pd.DataFrame(rows); d['ev'] = d.p * d.on + (1 - d.p) * d.off; d['evsim'] = d.psim * d.on + (1 - d.psim) * d.off
c = d.groupby('key')[['off', 'on', 'p', 'ev', 'evsim']].mean(); c['actual'] = act.loc[c.index]
res = {'n_decks': len(d), 'n_cards': len(c)}
for col in ['ev', 'evsim', 'on', 'off']:
    res[col] = {'pearson': float(c[col].corr(c.actual)), 'spearman': float(c[col].corr(c.actual, method='spearman')), 'mae_pp': float((c[col] - c.actual).abs().mean()), 'mean': float(c[col].mean())}
res['mae_zero'] = float(c.actual.abs().mean()); res['sd_actual'] = float(c.actual.std())
g = lambda k: float(c.loc[k, 'on']) if k in c.index else np.nan
res['on_rite'] = g('FDN|Rite of the Dragoncaller'); res['on_aa'] = g('MSH|Avengers Assemble!')
res['named'] = {k: {x: float(c.loc[k, x]) for x in ['off', 'on', 'p', 'ev', 'actual']} for k in c.index if k.split('|')[1] in ['Avengers Assemble!', 'Rite of the Dragoncaller', 'Smile at Death', 'Agent Phil Coulson', 'Doubling Season', 'Arahbo, the First Fang', 'Necroduality', 'Chronicle of Victory']}
e = res['ev']
res['rule_f20'] = {'pearson': e['pearson'] >= .62, 'spearman': e['spearman'] >= .40, 'rite_below_aa': bool(res['on_rite'] < res['on_aa']), 'adds_information': e['mae_pp'] < res['mae_zero']}
res['rule_f20']['pass'] = all(res['rule_f20'].values())
json.dump(res, open(H / 'result.json', 'w'), indent=1, default=float); print(json.dumps(res, indent=1, default=float)); c.to_csv(H / 'card_scores.csv')
