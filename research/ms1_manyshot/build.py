"""Build many-shot example/target files for one target set (R/M only).
  python3 build.py MSH|HOB|FRA
Examples: 30 random R/M per training set (all 28 OOF sets minus the target), names hidden (~)."""
import sys, gzip, json, re, pandas as pd, numpy as np
from pathlib import Path
H = Path(__file__).resolve().parent; R = H.parents[1]; C = R/'research/c9_power_questions'
T = sys.argv[1]; out = H/T; out.mkdir(exist_ok=True)
u = pd.read_csv(C/'cards.csv.gz', keep_default_na=False)
k2 = {k: r for r in u.itertuples() for k in r.keys.split(';')}
o = pd.read_csv(C/'oof_B10.csv.gz'); o['key'] = o.set+'|'+o.name
o['delta'] = (o.actual_gih-o.groupby('set').actual_gih.transform('mean'))*100
o['pdelta'] = (o.pred-o.groupby('set').pred.transform('mean'))*100
RM = {2: 'R', 3: 'M'}
def fmt(tag, rar, mv, col, typ, pt, txt):
    return f"{tag} | {rar} | MV {mv} {col or 'C'} | {typ}{' | '+pt if pt else ''}\n{txt}"
def fc(r, tag):
    c = k2[r.key]; return fmt(tag, RM[r.rarity_ord], c.mv, c.colors, c.type_line, c.pt, c.btext)
rm = o[o.rarity_ord >= 2]
ex = rm[rm.set != T].groupby('set', group_keys=False).apply(lambda g: g.sample(min(len(g), 30), random_state=1)).sample(frac=1, random_state=2)
(out/'examples.txt').write_text('\n'.join(fc(r, f'#E{i+1}')+f"\n=> {r.delta:+.1f}\n" for i, r in enumerate(ex.itertuples())))
if T != 'FRA':
    tg = rm[rm.set == T].sample(frac=1, random_state=3).reset_index(drop=True)
    (out/'targets.txt').write_text('\n\n'.join(fc(r, f'#T{i+1}') for i, r in enumerate(tg.itertuples()))+'\n')
    tg[['key', 'rarity_ord', 'delta', 'pdelta']].assign(tid=[f'T{i+1}' for i in range(len(tg))]).to_csv(out/'targets_key.csv', index=False)
else:
    P = Path('/home/claude/pageswt/data/target.json.gz')
    cards = json.load(gzip.open(P))['cards']
    fr = pd.read_csv(C/'fra_frozen_predictions.csv')
    act = pd.read_csv(H/'FRA_gih_public_20261017.csv')
    act = act[act.gih_games >= 500].set_index('card_name').gih_wr
    fr = fr[fr.name.isin(act.index)].copy(); fr['actual'] = fr.name.map(act)
    fr['delta'] = (fr.actual-fr.actual.mean())*100; fr['pdelta'] = (fr.pred_B10-fr.pred_B10.mean())*100
    cd = {c['id']: c for c in cards}
    fr['rar'] = fr.id.map(lambda i: cd[i]['rarity'])
    tg = fr[fr.rar.isin(['rare', 'mythic'])].sample(frac=1, random_state=3).reset_index(drop=True)
    L = []
    for i, r in enumerate(tg.itertuples()):
        c = cd[r.id]; nm = c['name']
        txt = re.sub(r'\{o([^}]*)\}', lambda m: ''.join('{'+t+'}' for t in m.group(1).split('o') if t), c['oracle_text'].replace('\r', ''))
        for part in [nm] + ([nm.split(',')[0]] if ',' in nm else []):
            txt = txt.replace(part, '~')
        txt = ' / '.join(t for t in txt.split('\n') if t)
        pt = f"{c['power']}/{c['toughness']}" if c['power'] else ''
        L.append(fmt(f'#T{i+1}', 'M' if c['rarity'] == 'mythic' else 'R', int(c['cmc']), ''.join(c['colors']), c['type_line'], pt, txt))
    (out/'targets.txt').write_text('\n\n'.join(L)+'\n')
    tg.assign(key='FRA|'+tg.name, rarity_ord=tg.rar.map({'rare': 2, 'mythic': 3}), tid=[f'T{i+1}' for i in range(len(tg))])[['key', 'rarity_ord', 'delta', 'pdelta', 'tid']].to_csv(out/'targets_key.csv', index=False)
print(T, len(ex), len(tg))
