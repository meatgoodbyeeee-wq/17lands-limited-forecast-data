import os, sys, random, re, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen, pandas as pd
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
FD = sys.argv[1]; D = '/root/.forge/decks/constructed'; pair = 'WU'
fn = set()
for r, _, fs in os.walk(FD + '/forge-gui/res/cardsfolder'): fn |= {norm(f[:-4]) for f in fs if f.endswith('.txt')}
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
o = pd.read_csv(R + '/c9_power_questions/oof_B10.csv.gz'); o = o[o.set == 'MSH'].copy(); o['a'] = (o.actual_gih - o.actual_gih.mean()) * 100
p = gen.pool('MSH').set_index('name')
base_lines = [l for l in open(f'{D}/j2_V.dck').read().splitlines() if '|MSH' in l and 'Avengers Assemble' not in l]
inbase = {l.split(' ', 1)[1].split('|')[0] for l in base_lines}
def cands(maxrar, win):
    out = []
    for _, r in o.iterrows():
        n = r['name']
        if n not in p.index or n in inbase or r.rarity_ord > maxrar or abs(r.a) > win: continue
        q = p.loc[n]
        if 'Creature' in q.tl or 'Legendary' in q.tl or not set(q.colors) <= set(pair) or norm(n) not in fn: continue
        out.append(n)
    return out
for maxrar, win in [(0, 2), (1, 2), (1, 3)]:
    c = cands(maxrar, win); print(f'rarity<={maxrar} window {win}: {len(c)}')
    if len(c) >= 12: break
else: sys.exit('not enough candidates')
used = set()
for k in (1, 2, 3):
    ch = random.Random(100 + k).sample([x for x in c if x not in used], 4); used |= set(ch)
    open(f'{D}/j2_B{k}c.dck', 'w').write('\n'.join(['[metadata]', f'Name=j2_B{k}c', '[Main]'] + base_lines + [f'1 {n}|MSH' for n in ch] + ['8 Plains', '9 Island']) + '\n')
    print(k, ch, [round(o[o.name == n].a.iloc[0], 1) for n in ch])
