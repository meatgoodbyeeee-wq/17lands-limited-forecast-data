"""Forced-inclusion pilot: card X is added to natural pools 00-02 and must be in the deck."""
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
c = pd.read_csv(HERE.parent / 'c11_set_reading_synergy/set_cards.csv.gz', keep_default_na=False)
FOCUS = {'MSH': ['Avengers Assemble!', 'Agent Phil Coulson', 'Thunderbolts Conspiracy'], 'FDN': ['Rite of the Dragoncaller', 'Doubling Season', 'Arahbo, the First Fang']}
RN = {0: 'C', 1: 'U', 2: 'R', 3: 'M'}
rows = []
for s, names in FOCUS.items():
    g = c[c.set == s].set_index('id')
    for n in names:
        fid = int(c[c.key == f'{s}|{n}'].id.iloc[0])
        for p in range(3):
            base = (HERE / 'pools' / f'{s}_{p:02d}.txt').read_text()
            r = g.loc[fid]; pt = f' | {r.pt}' if r.pt else ''
            entry = f"#{fid} | {RN[int(r.rar)]} | MV {int(float(r.mv))} {r.colors or 'colourless'} | {r.type}{pt}\n{r.text}"
            if f'#{fid} |' not in base:
                base = base.rstrip('\n') + '\n\n' + entry + '\n'
            name = f'{s}_{p:02d}_{fid}'
            (HERE / 'forced_pools' / f'{name}.txt').write_text(f"FORCED CARD: #{fid} (must be in your deck)\n\n{entry}\n\n" + base)
            rows.append({'name': name, 'set': s, 'card': n, 'id': fid, 'pool': f'{s}_{p:02d}'})
pd.DataFrame(rows).to_csv(HERE / 'forced.csv', index=False); print(len(rows))
