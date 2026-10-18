import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen
from collections import Counter
D = '/root/.forge/decks/constructed'; pair = 'WU'; rng = random.Random(20261019)
p = gen.pool('MSH'); AA = 'Avengers Assemble!'
print('pool', len(p), 'AA in pool', AA in set(p.name))
ok = p[p.colors.map(lambda c: set(c) <= set(pair))]
hero = [n for n, tl in zip(ok.name, ok.tl) if 'Hero' in tl and n != AA]; print('Hero cards in pair', len(hero))
base = rng.sample(hero, min(9, len(hero)))
rest = [n for n in ok.name if n != AA and n not in base]
base += rng.sample(rest, 19 - len(base)); extra = rng.sample([n for n in rest if n not in base], 4)
def write(path, spells):
    ct = Counter(spells)
    lines = ['[metadata]', 'Name=' + os.path.basename(path)[:-4], '[Main]'] + [f'{n} {nm}|MSH' for nm, n in ct.items()] + ['8 Plains', '9 Island']
    open(path, 'w').write('\n'.join(lines) + '\n')
write(f'{D}/j2_V.dck', base + [AA] * 4); write(f'{D}/j2_B.dck', base + extra)
for i, pr in enumerate(['WR', 'UB', 'BR', 'RG']): gen.write(f'{D}/j2_opp{i}.dck', 'MSH', gen.deck(p, pr, rng), pr)
print('V spells', len(base) + 4, 'Hero in base', sum(n in hero for n in base), 'extra', extra)
