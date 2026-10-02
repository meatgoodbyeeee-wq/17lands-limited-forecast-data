#!/usr/bin/env python3
"""Blind C4 extraction queue: reuses the C3 queues (blinded texts of 21 research sets + FRA, and the 7 newer sets).

  python build_queue.py build       # -> cards.csv.gz
  python build_queue.py --show N    # print batch N
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = 20261002
BATCH = 150


def build():
    a = pd.read_csv(ROOT / 'research/gih_llm_extract/cards.csv.gz', keep_default_na=False)
    b = pd.read_csv(ROOT / 'research/case6/c3_cards_new.csv.gz', keep_default_na=False)
    cols = ['keys', 'type_line', 'btext', 'mv', 'colors', 'pt', 'auto']
    u = pd.concat([a[cols], b[cols]], ignore_index=True)
    u['sig'] = u['btext'] + '␟' + u['type_line'].astype(str) + '␟' + u['mv'].astype(str) + '␟' + u['pt'].astype(str)
    u = u.groupby('sig', sort=True).agg(keys=('keys', lambda k: ';'.join(sorted(set(';'.join(k).split(';'))))), type_line=('type_line', 'first'),
                                        btext=('btext', 'first'), mv=('mv', 'first'), colors=('colors', 'first'), pt=('pt', 'first'),
                                        auto=('auto', 'max')).reset_index(drop=True)
    rng = np.random.default_rng(SEED)
    u = u.iloc[rng.permutation(len(u))].reset_index(drop=True)
    u['id'] = np.arange(1, len(u) + 1)
    u.to_csv(HERE / 'cards.csv.gz', index=False, compression='gzip')
    todo = int((u['auto'] == 0).sum())
    q = u[u['auto'] == 0].reset_index(drop=True)
    (HERE / 'input').mkdir(exist_ok=True)
    for n in range(int(np.ceil(todo / BATCH))):
        part = q.iloc[n * BATCH:(n + 1) * BATCH]
        lines = []
        for r in part.itertuples():
            head = f"#{r.id} | MV {r.mv} {r.colors or 'C'} | {r.type_line}" + (f" | {r.pt}" if r.pt else "")
            lines.append(head + "\n" + str(r.btext).replace("\n", " / ") + "\n")
        (HERE / f'input/b{n:02d}.txt').write_text("\n".join(lines) + f"-- batch {n}: ids {part['id'].min()}..{part['id'].max()}, {len(part)} cards\n")
    print({'unique': len(u), 'auto_zero': int(u['auto'].sum()), 'to_extract': todo, 'batches': int(np.ceil(todo / BATCH))})


if __name__ == '__main__':
    build()
