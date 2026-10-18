"""I1 analysis (Rule F21). python3 i1.py"""
import json, re
from pathlib import Path
import numpy as np, pandas as pd
H = Path(__file__).resolve().parent; R = H.parent
LINE = re.compile(r'#?([A-Z0-9_]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s*\|?\s*(.*)')
F1L = re.compile(r'#?([A-Z0-9_]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([\d.]+)')
w = pd.read_csv(H / 'weights.csv').set_index('name')
act = pd.read_csv(R / 'c9_power_questions/oof_B10.csv.gz'); act['c'] = (act.actual_gih - act.groupby('set').actual_gih.transform('mean')) * 100
act['key'] = act.set + '|' + act.name; act = act.set_index('key').c
sub = pd.read_csv(R / 'h1_judge_reliability/subset.csv'); rows = []
for r in sub.itertuples():
    p = H / 'out' / f'{r.name}.txt'; m = LINE.match(p.read_text().strip()) if p.exists() else None
    if not (m and m.group(1) in (str(r.id), r.name)): continue
    off, o1, o2, o3 = (float(m.group(i)) for i in range(2, 6)); ww = w.loc[r.name]
    if ww.fallback:
        pj = float(F1L.match((R / 'f1_ref_anchor/out' / f'{r.name}.txt').read_text().strip()).group(4)) / 100; W = [1 - pj, pj, 0, 0]
    else: W = [ww.w0, ww.w1, ww.w2, ww.w3]
    rows.append({'name': r.name, 'key': r.key, 'off': off, 'on1': o1, 'on2': o2, 'on3': o3, 'ev': W[0] * off + W[1] * o1 + W[2] * o2 + W[3] * o3})
d = pd.DataFrame(rows); c = d.groupby('key')[['off', 'on1', 'on2', 'on3', 'ev']].mean(); c['actual'] = act.loc[c.index]
res = {'n_decks': len(d), 'n_cards': len(c)}
for col in ['ev', 'on1', 'on3', 'off']:
    res[col] = {'pearson': float(c[col].corr(c.actual)), 'spearman': float(c[col].corr(c.actual, method='spearman')), 'mae_pp': float((c[col] - c.actual).abs().mean())}
res['mae_zero'] = float(c.actual.abs().mean())
res['named'] = {k: {x: round(float(c.loc[k, x]), 2) for x in ['off', 'on1', 'on2', 'on3', 'ev', 'actual']} for k in c.index if k.split('|')[1] in ['Avengers Assemble!', 'Rite of the Dragoncaller', 'Smile at Death', 'Agent Phil Coulson', 'Doubling Season', 'Arahbo, the First Fang', 'Necroduality', 'Chronicle of Victory']}
ev = lambda k: float(c.loc[k, 'ev'])
e = res['ev']; res['rule_f21'] = {'pearson': e['pearson'] >= .62, 'spearman': e['spearman'] >= .49,
    'rite_below_aa': ev('FDN|Rite of the Dragoncaller') < ev('MSH|Avengers Assemble!'), 'adds_information': e['mae_pp'] < res['mae_zero']}
res['rule_f21']['pass'] = all(res['rule_f21'].values())
c.to_csv(H / 'card_scores.csv'); json.dump(res, open(H / 'result.json', 'w'), indent=1); print(json.dumps(res, indent=1))
