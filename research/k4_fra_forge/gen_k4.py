"""K4 deck generator for FRA (same as gen_k3.py; FRA card names come from fra_frozen_predictions.csv because cards.csv keys use ids).
python3 gen_k4.py <FORGE_DIR> <OUT_DIR> [njobs] [decks_per_job]"""
import os, sys, random, re, unicodedata, itertools
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
HERE = os.path.dirname(os.path.abspath(__file__)); C9 = HERE + '/../c9_power_questions'
FD, OUT = sys.argv[1], sys.argv[2]; NJ = int(sys.argv[3]) if len(sys.argv) > 3 else 8; ND = int(sys.argv[4]) if len(sys.argv) > 4 else 40
CODE = 'FRA'
c = pd.read_csv(C9 + '/cards.csv.gz'); f = pd.read_csv(C9 + '/fra_frozen_predictions.csv')
c = c[c['keys'].astype(str).str.contains('FRA\\|')].copy(); c['id'] = c['keys'].str.extract(r'FRA\|(\w+)')[0]
c = c.merge(f[['id', 'name']], on='id'); 
c = c[(c.auto != 1) & ~c.type_line.str.contains('Land', na=False) & ~c.name.str.contains('//')]
c = c.assign(tl=c.type_line, colors=c.colors.fillna('')).drop_duplicates('name')
fn = set()
for r, _, fs in os.walk(FD + '/forge-gui/res/cardsfolder'): fn |= {norm(x[:-4]) for x in fs if x.endswith('.txt')}
p = c[[norm(n) in fn for n in c.name]].reset_index(drop=True)
PAIRS = [''.join(x) for x in itertools.combinations('WUBRG', 2)]; rng = random.Random(20261019)
ok = {pr: p[p.colors.map(lambda col, pr=pr: set(col) <= set(pr))] for pr in PAIRS}
cnt = 0
for j in range(NJ):
    d = f'{OUT}/job{j}'; os.makedirs(d, exist_ok=True)
    for i in range(ND):
        pr = rng.choice(PAIRS); pool = ok[pr]
        while True:
            sp = rng.sample(list(pool.name), 23); ncr = sum('Creature' in pool.set_index('name').loc[n].tl for n in sp)
            if 11 <= ncr <= 17: break
        name = f'fra_j{j}_d{i}_{pr}'
        lines = ['[metadata]', f'Name={name}', '[Main]'] + [f'1 {n}|{CODE}' for n in sp] + [f'8 {gen.BASIC[pr[0]]}', f'9 {gen.BASIC[pr[1]]}']
        open(f'{d}/{name}.dck', 'w').write('\n'.join(lines) + '\n'); cnt += 1
print('decks', cnt, 'cards in pool', len(p))
