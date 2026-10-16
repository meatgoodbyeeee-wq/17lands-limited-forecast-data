"""Pilot A1: sealed-style pools (6 packs: 10C 3U 1R/M, mythic 1/8), names hidden. Pools 0-5 natural, 6-11 with the focus card added."""
import random
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
c = pd.read_csv(HERE.parent / 'c11_set_reading_synergy/set_cards.csv.gz', keep_default_na=False)
FOCUS = {'MSH': 'Avengers Assemble!', 'FDN': 'Rite of the Dragoncaller'}
RN = {0: 'C', 1: 'U', 2: 'R', 3: 'M'}
rows = []
for s, focus in FOCUS.items():
    g = c[(c.set == s) & ~c['type'].str.startswith('Basic')]
    by = {r: g[g.rar == r] for r in range(4)}
    fid = int(g[g.key == f'{s}|{focus}'].id.iloc[0])
    for p in range(12):
        rnd = random.Random(f'{s}-{p}')
        ids = []
        for _ in range(6):
            ids += rnd.sample(list(by[0].id), 10) + rnd.sample(list(by[1].id), 3)
            ids.append(rnd.choice(list(by[3].id if rnd.random() < 1 / 8 else by[2].id)))
        if p >= 6 and fid not in ids:
            ids.append(fid)
        rnd.shuffle(ids)
        lines = []
        for i in ids:
            r = g[g.id == i].iloc[0]
            pt = f' | {r.pt}' if r.pt else ''
            lines.append(f"#{i} | {RN[int(r.rar)]} | MV {int(float(r.mv))} {r.colors or 'colourless'} | {r.type}{pt}\n{r.text}")
        name = f'{s}_{p:02d}'
        (HERE / 'pools' / f'{name}.txt').write_text(f"SEALED POOL ({len(ids)} cards, names hidden, ~ = the card itself). Basic lands are unlimited.\n\n" + '\n\n'.join(lines) + '\n')
        rows += [{'pool': name, 'set': s, 'id': i, 'key': g[g.id == i].key.iloc[0]} for i in ids]
pd.DataFrame(rows).to_csv(HERE / 'pools.csv', index=False)
print(len(rows), 'pool entries')
