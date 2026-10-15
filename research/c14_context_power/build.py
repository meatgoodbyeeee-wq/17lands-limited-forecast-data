"""Build C14 inputs: whole set list; every card is judged (s1 id order, s2 shuffled order)."""
import random
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
RN = {0: 'C', 1: 'U', 2: 'R', 3: 'M'}
c = pd.read_csv(HERE / 'set_cards.csv.gz', keep_default_na=False)
mp = pd.read_csv(HERE / 'mapping.csv').set_index('set')['code'].to_dict()
for p in ('s1', 's2'):
    (HERE / 'input' / p).mkdir(parents=True, exist_ok=True)
for s, g in c.groupby('set'):
    rows = list(g.sort_values('id').itertuples())
    for p in ('s1', 's2'):
        rr = rows[:]
        if p == 's2':
            random.Random(20261015 + len(rr)).shuffle(rr)
        lines = []
        for r in rr:
            pt = f' | {r.pt}' if r.pt else ''
            lines.append(f"#{r.id} | {RN[int(r.rar)]} freq {float(r.freq):.2f} | MV {int(float(r.mv))} {r.colors or 'colourless'} | {r.type}{pt}\n{r.text}")
        head = (f"SET LIST: {len(rr)} cards of one Limited set. Line format: #id | rarity (C common, U uncommon, R rare, M mythic) and freq = expected number of copies of that card a drafter sees in 3 packs | "
                "mana value and colours | type line | P/T, then rules text. Names are hidden (~ = the card itself).\n\nJudge EVERY card of this list, in this order.\n\n")
        (HERE / 'input' / p / f'{mp[s]}.txt').write_text(head + '\n\n'.join(lines) + '\n')
print(len(c), 'cards', c['set'].nunique(), 'sets')
