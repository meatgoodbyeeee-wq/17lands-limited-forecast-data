import pandas as pd, random
from pathlib import Path
A2 = Path(__file__).resolve().parents[1] / 'a2_forced_deck_ev'
sel = pd.read_csv(A2 / 'selected.csv'); dl = pd.read_csv(A2 / 'decklist.csv')
NAMED = ['MSH|Avengers Assemble!', 'FDN|Rite of the Dragoncaller', 'TDM|Smile at Death', 'MSH|Agent Phil Coulson', 'FDN|Doubling Season',
         'FDN|Arahbo, the First Fang', 'VOW|Necroduality', 'ECL|Chronicle of Victory']
keys = sel[~sel.key.isin(NAMED)]; rng = random.Random(20261018)
pick = list(sel[sel.key.isin(NAMED)].itertuples()) + [keys.iloc[i] for i in []]
rest = keys.sample(n=22, random_state=20261018)
cards = pd.concat([sel[sel.key.isin(NAMED)], rest])[['set', 'id', 'key']]
d = dl.merge(cards, on=['set', 'id'])
d[['name', 'set', 'id', 'key']].to_csv('subset.csv', index=False)
names = list(d.name)
for i in range(0, len(names), 10): Path(f'batches/b{i // 10:02d}.txt').write_text('\n'.join(names[i:i + 10]) + '\n')
print(len(cards), len(d), (len(names) + 9) // 10)
