"""A2 forced-deck EV (Rule F16, see PLAN.md).
python3 a2.py select|pools|batches <stage>|enab_in|judge_in|features|check|arm <name>|evaluate
"""
import json, random, re, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; RES = HERE.parent
CARDS = pd.read_csv(RES / 'c11_set_reading_synergy/set_cards.csv.gz', keep_default_na=False)
RN = {0: 'C', 1: 'U', 2: 'R', 3: 'M'}


def entry(r):
    pt = f' | {r.pt}' if r.pt else ''
    return f"#{r.id} | {RN[int(r.rar)]} | MV {int(float(r.mv))} {r.colors or 'colourless'} | {r.type}{pt}\n{r.text}"


def select():
    f = pd.read_csv(RES / 'c11_set_reading_synergy/c11_features.csv')[['key', 'c11_pay']]
    t = CARDS[(CARDS.target == 1) & (CARDS.rar >= 2)].merge(f, on='key', how='left')
    t['c11_pay'] = t['c11_pay'].fillna(-1)
    sel = t.sort_values(['set', 'c11_pay', 'rar', 'id'], ascending=[True, False, False, True]).groupby('set').head(10)
    sel[['set', 'id', 'key', 'rar', 'c11_pay']].to_csv(HERE / 'selected.csv', index=False); print(len(sel))


def pools():
    sel = pd.read_csv(HERE / 'selected.csv'); rows = []
    for r in sel.itertuples():
        g = CARDS[(CARDS.set == r.set) & ~CARDS['type'].str.startswith('Basic')]
        by = {k: list(g[g.rar == k].id) for k in range(4)}; gi = g.set_index('id')
        for k in range(3):
            rnd = random.Random(f'A2-{r.set}-{r.id}-{k}'); ids = []
            for _ in range(6):
                ids += rnd.sample(by[0], 10) + rnd.sample(by[1], 3)
                ids.append(rnd.choice(by[3] if (rnd.random() < 1 / 8 and by[3]) else by[2]))
            if r.id not in ids: ids.append(r.id)
            rnd.shuffle(ids)
            fx = gi.loc[r.id]; fx_e = entry(pd.Series({**fx.to_dict(), 'id': r.id}).pipe(lambda s: type('R', (), s.to_dict())))
            body = '\n\n'.join(entry(type('R', (), {**gi.loc[i].to_dict(), 'id': i})) for i in ids)
            name = f'{r.set}_{r.id}_{k}'
            (HERE / 'pools' / f'{name}.txt').write_text(f"FORCED CARD: #{r.id} (must be in your deck)\n\n{fx_e}\n\nSEALED POOL ({len(ids)} cards, names hidden, ~ = the card itself). Basic lands are unlimited.\n\n{body}\n")
            rows.append({'name': name, 'set': r.set, 'id': r.id, 'k': k})
    pd.DataFrame(rows).to_csv(HERE / 'decklist.csv', index=False); print(len(rows))


def batches(stage, size):
    names = list(pd.read_csv(HERE / 'decklist.csv')['name'])
    for i in range(0, len(names), size):
        (HERE / 'batches' / f'{stage}_{i // size:03d}.txt').write_text('\n'.join(names[i:i + size]) + '\n')
    print(stage, (len(names) + size - 1) // size)


def deck_ids(name):
    t = (HERE / 'decks' / f'{name}.txt').read_text()
    return [int(x) for x in re.findall(r'#(\d+)', t.split('BASICS')[0])]


def enab_in():
    dl = pd.read_csv(HERE / 'decklist.csv'); bad = []
    for r in dl.itertuples():
        p = HERE / 'decks' / f'{r.name}.txt'
        if not p.exists(): bad.append((r.name, 'missing')); continue
        ids = deck_ids(r.name)
        if r.id not in ids: bad.append((r.name, 'forced card absent'))
        gi = CARDS[CARDS.set == r.set].set_index('id')
        ids = [i for i in ids if i in gi.index]
        body = '\n\n'.join(entry(type('R', (), {**gi.loc[i].to_dict(), 'id': i})) for i in ids)
        (HERE / 'enab_in' / f'{r.name}.txt').write_text(f'DECK (non-basic cards; the rest are basic lands):\n\n{body}\n\nTARGET card: #{r.id}\n')
    print('problems', bad)


def judge_in():
    dl = pd.read_csv(HERE / 'decklist.csv'); miss = []
    for r in dl.itertuples():
        e = HERE / 'enab_out' / f'{r.name}.txt'
        if not e.exists(): miss.append(r.name); continue
        (HERE / 'judge_in' / f'{r.name}.txt').write_text((HERE / 'enab_in' / f'{r.name}.txt').read_text() + '\n\nENABLERS IN THIS DECK (id, MV, order relative to target, reason):\n' + e.read_text())
    print('missing enablers', miss)


LINE = re.compile(r'#?([A-Z0-9_]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\|?\s*(.*)')


def features():
    dl = pd.read_csv(HERE / 'decklist.csv'); rows = []; bad = []
    for r in dl.itertuples():
        p = HERE / 'judge_out' / f'{r.name}.txt'
        m = LINE.match(p.read_text().strip()) if p.exists() else None
        if not m or m.group(1) not in (str(r.id), r.name): bad.append(r.name); continue
        off, on, pp = float(m.group(2)), float(m.group(3)), float(m.group(4)) / 100
        rows.append({'name': r.name, 'set': r.set, 'id': r.id, 'off': off, 'on': on, 'p': pp, 'ev': pp * on + (1 - pp) * off})
    d = pd.DataFrame(rows); print('bad', bad)
    sel = pd.read_csv(HERE / 'selected.csv')
    f = d.groupby(['set', 'id'])[['off', 'on', 'p', 'ev']].mean().reset_index().merge(sel[['set', 'id', 'key']], on=['set', 'id'])
    d.to_csv(HERE / 'deck_judgements.csv', index=False); f.to_csv(HERE / 'a2_features.csv', index=False)
    print(len(f)); print(f[['off', 'on', 'p', 'ev']].describe().round(2))


if __name__ == '__main__':
    a = sys.argv[1:]
    {'select': select, 'pools': pools, 'enab_in': enab_in, 'judge_in': judge_in, 'features': features,
     'batches': lambda: batches(a[1], int(a[2]))}[a[0]]()
