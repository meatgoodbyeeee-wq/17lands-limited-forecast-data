"""G3.1 inputs (deterministic). python3 build.py"""
import gzip, json, re, numpy as np, pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
H = Path(__file__).resolve().parent; R = H.parents[1]; C = R/'research/c9_power_questions'; X = R/'research/x1_expert_grades'
TARGETS = ['FRA', 'TMT', 'ECL']
PAST = ['BLB','DFT','DSK','ECL','EOE','FDN','LCI','MKM','OTJ','SOS','TDM','TLA','TMT']
LESSON_SETS = [s for s in PAST if s not in TARGETS]
def nm(s): return re.sub(r'[^a-z0-9]', '', str(s).split('//')[0].lower())
u = pd.read_csv(C/'cards.csv.gz', keep_default_na=False); k2 = {k: r for r in u.itertuples() for k in r.keys.split(';')}
o = pd.read_csv(C/'oof_B10.csv.gz'); o['key'] = o.set+'|'+o.name
rows = []
for r in o.itertuples():
    c = k2[r.key]; rows.append(dict(set=r.set, name=r.name, key=r.key, rar=r.rarity_ord, mv=c.mv, col=c.colors, typ=c.type_line, pt=c.pt, txt=c.btext, actual=r.actual_gih))
cards = {c['id']: c for c in json.load(gzip.open('/home/claude/pageswt/data/target.json.gz'))['cards']}
fr = pd.read_csv(C/'fra_frozen_predictions.csv').merge(pd.read_csv(X/'fra_actual_public_20261017.csv'), on='name'); fr = fr[fr.gih_games >= 500]
RO = {'common': 0, 'land': 0, 'uncommon': 1, 'rare': 2, 'mythic': 3}
for r in fr.itertuples():
    c = cards[r.id]; t = re.sub(r'\{o([^}]*)\}', lambda m: ''.join('{'+x+'}' for x in m.group(1).split('o') if x), c['oracle_text'].replace('\r', ''))
    for part in [c['name']] + ([c['name'].split(',')[0]] if ',' in c['name'] else []): t = t.replace(part, '~')
    rows.append(dict(set='FRA', name=c['name'], key='FRA|'+r.id, rar=RO[c['rarity']], mv=int(c['cmc']), col=''.join(c['colors']), typ=c['type_line'],
                     pt=f"{c['power']}/{c['toughness']}" if c['power'] else '', txt=' / '.join(x for x in t.split('\n') if x), actual=r.actual_gih))
A = pd.DataFrame(rows)
G = {}
for s in PAST + ['FRA']:
    g = pd.read_csv(X/f'grades/{s}.csv'); g = g[pd.to_numeric(g.rating, errors='coerce').notna()]
    G[s] = g.assign(k=g.name.map(nm)).drop_duplicates('k').set_index('k').rating.astype(float)
A['grade'] = [G[s].get(nm(n), np.nan) if s in G else np.nan for s, n in zip(A.set, A.name)]
A['y'] = (A.actual - A.groupby('set').actual.transform('mean'))*100
RAR = 'CURM'
def sec(c):
    c = c or ''
    return {'W': '1 White', 'U': '2 Blue', 'B': '3 Black', 'R': '4 Red', 'G': '5 Green'}.get(c, '6 Multicolour' if len(c) > 1 else '7 Colourless/Land')
A['sec'] = A.col.map(sec)
def fmt(tag, r, short=False):
    t = r.txt if not short or len(r.txt) < 220 else r.txt[:220]+'…'
    return f"{tag} | {RAR[r.rar]} | MV {r.mv} {r.col or 'C'} | {r.typ}{' | '+r.pt if r.pt else ''}\n{t}"
# lessons v2 material: per lesson set and colour, C/U cards sorted by expert grade with actual outcome
L = A[A.set.isin(LESSON_SETS) & A.grade.notna() & (A.rar <= 1)]
with open(H/'lesson_material_cu.txt', 'w') as f:
    f.write('For each past set and colour: commons/uncommons with the expert pre-release grade (0-5) and the actual GIH win rate minus set mean (pp). Sorted by expert grade.\n')
    for (s, c), g in L.groupby(['set', 'sec']):
        f.write(f'\n=== set {s} / {c[2:]} ===\n')
        for r in g.sort_values('grade', ascending=False).itertuples():
            f.write(f"{RAR[r.rar]} | MV {r.mv} | {r.typ}{' | '+r.pt if r.pt else ''} | {r.txt[:160]} || expert {r.grade:.1f} | actual {r.y:+.1f}\n")
# retrieval pool and per-target files
P = A[A.grade.notna()].reset_index(drop=True)
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit((A.typ+' '+A.txt).tolist())
PV = vec.transform((P.typ+' '+P.txt).tolist())
for T in TARGETS:
    out = H/T; out.mkdir(exist_ok=True); (H/'keys').mkdir(exist_ok=True)
    pool = P[P.set != T]; pv = PV[(P.set != T).values]
    cal = pool.sample(300, random_state=1)
    (out/'calibration.txt').write_text('\n'.join(fmt(f'#E{i+1}', r, True)+f"\n=> expert {r.grade:.1f}/5\n" for i, r in enumerate(cal.itertuples())))
    tg = A[A.set == T].sample(frac=1, random_state=3).sort_values('sec', kind='stable').reset_index(drop=True)
    tg['tid'] = [f'T{i+1}' for i in range(len(tg))]
    sims = (vec.transform((tg.typ+' '+tg.txt).tolist()) @ pv.T).toarray()
    with open(out/'targets.txt', 'w') as f:
        cur = None
        for i, r in enumerate(tg.itertuples()):
            if r.sec != cur:
                cur = r.sec; f.write(f'\n######## SECTION: {cur[2:]} ########\n\n')
            f.write(fmt('#'+r.tid, r)+'\n  similar past cards (expert grade):\n')
            for j in np.argsort(-sims[i])[:5]:
                q = pool.iloc[j]; f.write(f"    - {RAR[q.rar]} | MV {q.mv} {q.col or 'C'} | {q.typ}{' | '+q.pt if q.pt else ''} | {q.txt[:140]} => {q.grade:.1f}\n")
            f.write('\n')
    g3 = pd.read_csv(R/f'research/g3_expert_grade/{T}/targets_key.csv')
    tg[['tid', 'key', 'name', 'sec']].merge(g3.drop(columns='tid'), on=['key', 'name'], how='left').to_csv(H/'keys'/f'{T}.csv', index=False)
    print(T, len(tg), 'cal', len(cal), 'sections', tg.sec.value_counts().sort_index().to_dict())
print('lesson cu rows', len(L))
