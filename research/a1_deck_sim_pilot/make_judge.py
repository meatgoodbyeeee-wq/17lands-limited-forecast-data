import re
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
c = pd.read_csv(HERE.parent / 'c11_set_reading_synergy/set_cards.csv.gz', keep_default_na=False)
pools = pd.read_csv(HERE / 'pools.csv')
rows = []
for f in sorted((HERE / 'decks').glob('*.txt')):
    t = f.read_text(); s = f.stem[:3]
    ids = [int(x) for x in re.findall(r'#(\d+)', t.split('BASICS')[0])]
    pool = set(pools[pools.pool == f.stem].id)
    bad = [i for i in ids if i not in pool]
    g = c[c.set == s].set_index('id')
    nonland = [i for i in ids if 'Land' not in g.loc[i, 'type']]
    tg = [i for i in ids if g.loc[i, 'target'] == 1]
    print(f.stem, 'cards', len(ids), 'nonland', len(nonland), 'targets', len(tg), 'not-in-pool', bad)
    lines = []
    for i in ids:
        r = g.loc[i]; pt = f' | {r.pt}' if r.pt else ''
        lines.append(f"#{i} | MV {int(float(r.mv))} {r.colors or 'colourless'} | {r.type}{pt}\n{r.text}")
    (HERE / 'judge' / f'{f.stem}_in.txt').write_text('DECK (non-basic cards; the rest are basic lands):\n\n' + '\n\n'.join(lines) + '\n\nTARGET cards (judge in this order): ' + ' '.join(f'#{i}' for i in tg) + '\n')
    rows += [{'deck': f.stem, 'set': s, 'id': i, 'key': g.loc[i, 'key']} for i in ids]
pd.DataFrame(rows).to_csv(HERE / 'decks.csv', index=False)
