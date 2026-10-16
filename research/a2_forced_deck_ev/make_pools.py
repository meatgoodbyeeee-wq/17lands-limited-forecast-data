"""A2 step 1: select 10 R/M theme cards per set (highest C11 PAY) and build 3 forced sealed pools each."""
import random
from pathlib import Path
import pandas as pd
H = Path(__file__).resolve().parent
c = pd.read_csv(H.parent / 'c11_set_reading_synergy/set_cards.csv.gz', keep_default_na=False)
pay = pd.read_csv(H.parent / 'c11_set_reading_synergy/c11_features.csv').set_index('key')['c11_pay']
RN = {0: 'C', 1: 'U', 2: 'R', 3: 'M'}
def entry(r):
    pt = f' | {r.pt}' if r.pt else ''
    return f"#{r.id} | {RN[int(r.rar)]} | MV {int(float(r.mv))} {r.colors or 'colourless'} | {r.type}{pt}\n{r.text}"
sel = []
for s, g in c.groupby('set'):
    t = g[(g.target == 1) & (g.rar >= 2)].copy(); t['pay'] = t.key.map(pay)
    t = t.sort_values(['pay', 'rar', 'id'], ascending=[False, False, True]).head(10)
    sel.append(t)
sel = pd.concat(sel)
rows = []
for r in sel.itertuples():
    g = c[(c.set == r.set) & ~c['type'].str.startswith('Basic')]
    by = {k: list(g[g.rar == k].id) for k in range(4)}
    gi = g.set_index('id')
    for k in range(3):
        rnd = random.Random(f'A2-{r.set}-{r.id}-{k}')
        ids = []
        for _ in range(6):
            ids += rnd.sample(by[0], 10) + rnd.sample(by[1], 3)
            ids.append(rnd.choice(by[3] if (rnd.random() < 1 / 8 and by[3]) else by[2]))
        if r.id not in ids: ids.append(r.id)
        rnd.shuffle(ids)
        name = f'{r.set}_{r.id}_{k}'
        body = '\n\n'.join(entry(gi.loc[i].rename(i) if False else type('R', (), dict(gi.loc[i].to_dict(), id=i))) for i in ids)
        (H / 'pools' / f'{name}.txt').write_text(f"FORCED CARD: #{r.id} (must be in your deck)\n\n{entry(r)}\n\nSEALED POOL ({len(ids)} cards, names hidden, ~ = the card itself). Basic lands are unlimited.\n\n{body}\n")
        rows.append({'name': name, 'set': r.set, 'id': r.id, 'key': r.key, 'k': k})
pd.DataFrame(rows).to_csv(H / 'manifest.csv', index=False)
print(len(sel), 'cards', len(rows), 'pools')
