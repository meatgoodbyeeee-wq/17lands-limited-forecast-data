import os, sys, random, re, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen, pandas as pd
from collections import Counter
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
FD = sys.argv[1]; D = '/root/.forge/decks/constructed'; pair = 'WU'
fn = set()
for r, _, fs in os.walk(FD + '/forge-gui/res/cardsfolder'): fn |= {norm(f[:-4]) for f in fs if f.endswith('.txt')}
o = pd.read_csv(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/c9_power_questions/oof_B10.csv.gz'); o = o[o.set == 'MSH']
o['a'] = (o.actual_gih - o.actual_gih.mean()) * 100
p = gen.pool('MSH').set_index('name')
vdeck = open(f'{D}/j2_V.dck').read(); base_lines = [l for l in vdeck.splitlines() if '|MSH' in l and 'Avengers Assemble' not in l]
inbase = {l.split(' ', 1)[1].split('|')[0] for l in base_lines}
cand = [r['name'] for _, r in o.iterrows() if r.rarity_ord == 0 and abs(r.a) <= 2.0 and r['name'] in p.index
        and set(p.loc[r['name']].colors) <= set(pair) and 'Legendary' not in p.loc[r['name']].tl and norm(r['name']) in fn and r['name'] not in inbase]
print('candidates', len(cand)); used = set()
for k in (1, 2, 3):
    ch = random.Random(k).sample([c for c in cand if c not in used], 4); used |= set(ch)
    lines = ['[metadata]', f'Name=j2_B{k}', '[Main]'] + base_lines + [f'1 {n}|MSH' for n in ch] + ['8 Plains', '9 Island']
    open(f'{D}/j2_B{k}.dck', 'w').write('\n'.join(lines) + '\n'); print(k, ch, [round(o[o.name == n].a.iloc[0], 1) for n in ch])
