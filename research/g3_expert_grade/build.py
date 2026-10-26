"""G3 inputs. python3 build.py   (deterministic; rerunning reproduces the same files)"""
import gzip, json, re, numpy as np, pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent; R = H.parents[1]; C = R/'research/c9_power_questions'; X = R/'research/x1_expert_grades'
TARGETS = ['FRA', 'TMT', 'ECL']
PAST = ['BLB','DFT','DSK','ECL','EOE','FDN','LCI','MKM','OTJ','SOS','TDM','TLA','TMT']
LESSON_SETS = [s for s in PAST if s not in TARGETS]          # 11 sets, never a target
def nm(s): return re.sub(r'[^a-z0-9]', '', str(s).split('//')[0].lower())
u = pd.read_csv(C/'cards.csv.gz', keep_default_na=False)
k2 = {k: r for r in u.itertuples() for k in r.keys.split(';')}
o = pd.read_csv(C/'oof_B10.csv.gz'); o['key'] = o.set+'|'+o.name
c9 = pd.read_csv(C/'c9_features.csv.gz').set_index('key')['c9_m_GRADE']
G = {}
for s in PAST + ['FRA']:
    g = pd.read_csv(X/f'grades/{s}.csv'); g = g[pd.to_numeric(g.rating, errors='coerce').notna()]
    G[s] = g.assign(k=g.name.map(nm)).drop_duplicates('k').set_index('k').rating.astype(float)
o['grade'] = [G[s].get(nm(n), np.nan) if s in G else np.nan for s, n in zip(o.set, o.name)]
RAR = 'CURM'
def fmt(tag, rar, mv, col, typ, pt, txt):
    return f"{tag} | {rar} | MV {mv} {col or 'C'} | {typ}{' | '+pt if pt else ''}\n{txt}"
def fc(key, rk, tag):
    c = k2[key]; return fmt(tag, RAR[rk], c.mv, c.colors, c.type_line, c.pt, c.btext)
# --- lesson material: disagreements AI GRADE vs expert, 11 non-target sets (names shown; lessons must be general)
L = o[o.set.isin(LESSON_SETS) & o.grade.notna() & o.key.isin(c9.index)].copy()
L['ai_grade'] = c9.loc[L.key].values
z = lambda s: (s - s.groupby(L.set).transform('mean'))/s.groupby(L.set).transform('std')
L['y'] = (L.actual_gih - L.groupby('set').actual_gih.transform('mean'))*100
L['b10_resid'] = L.y - (L.pred - L.groupby('set').pred.transform('mean'))*100
L['expert_minus_ai_z'] = z(L.grade) - z(L.ai_grade)
L = L.reindex(L.expert_minus_ai_z.abs().sort_values(ascending=False).index).head(400)
with open(H/'lesson_material.txt', 'w') as f:
    f.write('Columns: rarity | AI grade (0-10 scale) | expert grade (0-5) | actual GIH minus set mean (pp) | B10 model residual (actual - model, pp)\n\n')
    for r in L.itertuples():
        f.write(fc(r.key, r.rarity_ord, f'[{r.set}] {r.name}') + f"\nAI {r.ai_grade:.1f}/10 | expert {r.grade:.1f}/5 | actual {r.y:+.1f} | B10 resid {r.b10_resid:+.1f}\n\n")
# --- per target: examples (expert labels from other past sets) and targets (all scored cards)
for T in TARGETS:
    out = H/T; out.mkdir(exist_ok=True)
    ex = o[o.set.isin([s for s in PAST if s != T]) & o.grade.notna()]
    ex = ex.groupby('set', group_keys=False).apply(lambda g: g.sample(min(len(g), 66), random_state=1)).sample(frac=1, random_state=2)
    (out/'examples.txt').write_text('\n'.join(fc(r.key, r.rarity_ord, f'#E{i+1}') + f"\n=> expert {r.grade:.1f}/5\n" for i, r in enumerate(ex.itertuples())))
    if T != 'FRA':
        tg = o[o.set == T].sample(frac=1, random_state=3).reset_index(drop=True)
        (out/'targets.txt').write_text('\n\n'.join(fc(r.key, r.rarity_ord, f'#T{i+1}') for i, r in enumerate(tg.itertuples())) + '\n')
        key = pd.DataFrame({'tid': [f'T{i+1}' for i in range(len(tg))], 'key': tg.key, 'name': tg.name, 'rarity_ord': tg.rarity_ord,
                            'actual_gih': tg.actual_gih, 'pred': tg.pred, 'c9_grade': tg.key.map(c9), 'expert': tg.grade})
    else:
        cards = {c['id']: c for c in json.load(gzip.open('/home/claude/pageswt/data/target.json.gz'))['cards']}
        fr = pd.read_csv(C/'fra_frozen_predictions.csv'); a = pd.read_csv(X/'fra_actual_public_20261017.csv')
        fr = fr.merge(a, on='name'); fr = fr[fr.gih_games >= 500].sample(frac=1, random_state=3).reset_index(drop=True)
        txts = []
        for i, r in enumerate(fr.itertuples()):
            c = cards[r.id]; t = re.sub(r'\{o([^}]*)\}', lambda m: ''.join('{'+x+'}' for x in m.group(1).split('o') if x), c['oracle_text'].replace('\r', ''))
            for part in [c['name']] + ([c['name'].split(',')[0]] if ',' in c['name'] else []): t = t.replace(part, '~')
            t = ' / '.join(x for x in t.split('\n') if x); pt = f"{c['power']}/{c['toughness']}" if c['power'] else ''
            txts.append(fmt(f'#T{i+1}', {'common': 'C', 'land': 'C', 'uncommon': 'U', 'rare': 'R', 'mythic': 'M'}[c['rarity']], int(c['cmc']), ''.join(c['colors']), c['type_line'], pt, t))
        (out/'targets.txt').write_text('\n\n'.join(txts) + '\n')
        key = pd.DataFrame({'tid': [f'T{i+1}' for i in range(len(fr))], 'key': 'FRA|'+fr.id, 'name': fr.name,
                            'rarity_ord': fr.id.map(lambda i: {'common': 0, 'land': 0, 'uncommon': 1, 'rare': 2, 'mythic': 3}[cards[i]['rarity']]),
                            'actual_gih': fr.actual_gih, 'pred': fr.pred_B10, 'c9_grade': ('FRA|'+fr.id).map(c9),
                            'expert': fr.name.map(lambda n: G['FRA'].get(nm(n), np.nan))})
    key.to_csv(out/'targets_key.csv', index=False)
    print(T, 'examples', len(ex), 'targets', len(key), 'c9 missing', key.c9_grade.isna().sum(), 'expert graded', key.expert.notna().sum())
print('lesson rows', len(L))
