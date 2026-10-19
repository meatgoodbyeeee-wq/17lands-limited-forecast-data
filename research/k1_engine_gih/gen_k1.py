"""K1 deck generator. python3 gen_k1.py <FORGE_DIR> <OUT_DIR> [njobs] [decks_per_job]"""
import os, sys, random, re, unicodedata, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
FD, OUT = sys.argv[1], sys.argv[2]; NJ = int(sys.argv[3]) if len(sys.argv) > 3 else 8; ND = int(sys.argv[4]) if len(sys.argv) > 4 else 40
fn = set()
for r, _, fs in os.walk(FD + '/forge-gui/res/cardsfolder'): fn |= {norm(f[:-4]) for f in fs if f.endswith('.txt')}
p = gen.pool('MSH'); p = p[[norm(n) in fn for n in p.name]]
PAIRS = [''.join(c) for c in itertools.combinations('WUBRG', 2)]; rng = random.Random(20261019)
ok = {pr: p[p.colors.map(lambda c, pr=pr: set(c) <= set(pr))] for pr in PAIRS}
cnt = 0
for j in range(NJ):
    d = f'{OUT}/job{j}'; os.makedirs(d, exist_ok=True)
    for i in range(ND):
        pr = rng.choice(PAIRS); pool = ok[pr]
        while True:
            sp = rng.sample(list(pool.name), 23); ncr = sum('Creature' in pool.set_index('name').loc[n].tl for n in sp)
            if 11 <= ncr <= 17: break
        name = f'k1_j{j}_d{i}_{pr}'
        lines = ['[metadata]', f'Name={name}', '[Main]'] + [f'1 {n}|MSH' for n in sp] + [f'8 {gen.BASIC[pr[0]]}', f'9 {gen.BASIC[pr[1]]}']
        open(f'{d}/{name}.dck', 'w').write('\n'.join(lines) + '\n'); cnt += 1
print('decks', cnt, 'cards in pool', len(p))
