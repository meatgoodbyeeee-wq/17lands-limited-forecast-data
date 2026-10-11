#!/usr/bin/env python3
"""Build C11 set lists, targets and blinded inputs (before any judging). See PLAN.md.

  python3 build.py
"""
import json, random, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parent
sys.path.insert(0, str(R / 'c7c_draft_weighted'))
import c7c  # noqa: E402
SPEC_MIN = 1.5
PASSES = ['s1', 's2']


def main():
    u = pd.read_csv(R / 'c5_atomic_effects/cards.csv.gz', keep_default_na=False)
    rows = []
    for r in u.itertuples():
        for k in str(r.keys).split(';'):
            rows.append((k, r.id, r.type_line, r.btext, r.mv, r.colors, r.pt))
    c = pd.DataFrame(rows, columns=['key', 'id', 'type', 'text', 'mv', 'colors', 'pt'])
    rar = c7c.rarity_map(c7c.FRA_DEFAULT)
    c['rar'] = c['key'].map(rar)
    c = c[c['rar'].notna()].copy()
    c['rar'] = c['rar'].astype(int)
    w, layout = c7c.weights(c['key'].tolist(), rar)
    c['freq'] = w
    c['set'] = c['key'].str.split('|').str[0]
    c = c[~c['type'].str.contains('Basic')]
    c = c.drop_duplicates(['set', 'id']).reset_index(drop=True)
    f = pd.read_csv(R / 'c10_reasoned_rejudge/c10_features.csv')
    spec = f.set_index('id')['c10_spec']
    c['spec'] = c['id'].map(spec)
    c['target'] = (c['spec'] >= SPEC_MIN).astype(int)
    c.to_csv(HERE / 'set_cards.csv.gz', index=False, compression='gzip')
    sets = sorted(c['set'].unique())
    rnd = random.Random(20261010); order = sets[:]; rnd.shuffle(order)
    mapping = {s: f'S{i:02d}' for i, s in enumerate(order)}
    pd.DataFrame({'set': list(mapping), 'code': list(mapping.values())}).to_csv(HERE / 'mapping.csv', index=False)
    for p in PASSES:
        (HERE / 'input' / p).mkdir(parents=True, exist_ok=True)
    RN = {0: 'C', 1: 'U', 2: 'R', 3: 'M'}
    for s in sets:
        g = c[c['set'] == s]
        lines = []
        for r in g.sort_values('id').itertuples():
            pt = f' | {r.pt}' if r.pt else ''
            lines.append(f"#{r.id} | {RN[r.rar]} freq {r.freq:.2f} | MV {int(r.mv)} {r.colors or 'colourless'} | {r.type}{pt}\n{r.text}")
        tg = g[g['target'] == 1]
        for i, p in enumerate(PASSES):
            ids = [int(x) for x in tg['id']]
            if i == 1:
                random.Random(7 + len(ids)).shuffle(ids)
            head = (f"SET LIST: {len(g)} cards of one Limited set. Line format: #id | rarity (C common, U uncommon, R rare, M mythic) and freq = expected number of copies of that card a drafter sees in 3 packs | "
                    "mana value and colours | type line | P/T, then rules text. Names are hidden (~ = the card itself).\n\n")
            tail = '\n\nTARGET CARDS (judge exactly these, in this order): ' + ' '.join(f'#{x}' for x in ids) + '\n'
            (HERE / 'input' / p / f'{mapping[s]}.txt').write_text(head + '\n\n'.join(lines) + tail)
    print(len(c), 'cards', len(sets), 'sets', int(c['target'].sum()), 'targets', layout)
    print(c.groupby('set')['target'].sum().describe().round(1).to_dict())


if __name__ == '__main__':
    main()
