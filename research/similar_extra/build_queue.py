#!/usr/bin/env python3
"""Blinded labelling queue for the name_only references of the site's similar-card list.

  python3 build_queue.py <pages>/data/similar-references.json.gz

Writes label/cards.csv (one row per name_only card, ids 1..N in file order) and label/input/cNN.txt (60 cards per chunk).
Card view = the production view of research/trk_preview/trk_label.py (sonnet_check.card_view): name -> "~", no set, rarity or numbers,
mana value, colours, type line, P/T and rules text only. Nothing from 17Lands (GIH, ALSA, games) is shown. Blank-text creatures and basic lands are 'auto'
(no label call; zero labels, creature body = 1), like the TRK queue.
Labels (label/raw/cNN_{c3,c4,c5}.txt) were written in-context by the session model (claude-sonnet-5-5) following the unchanged RUBRIC.md of
gih_llm_extract (C3), c4_fine_effects (C4) and c5_atomic_effects (C5), one chunk at a time with all three passes from the same reading.
"""
import sys, gzip, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; R = HERE.parents[0]
sys.path.insert(0, str(R / 'gih_llm_extract'))
import build_input as bi  # noqa
n = json.loads(gzip.open(sys.argv[1], 'rt', encoding='utf-8').read())['name_only']
rows = []
for i, c in enumerate(n, 1):
    ty, tx = bi.gallery_to_scryfall(c['type_line']), bi.gallery_to_scryfall(c['oracle_text'] or '')
    pt = '' if c.get('power') in (None, '') else f"{bi.fmt_num(c['power'])}/{bi.fmt_num(c['toughness'])}"
    rows.append(dict(id=i, key=f"{c['set']}|{c['name']}", name=c['name'], set=c['set'], type_line=ty, text=tx, mv=bi.fmt_num(c['cmc']), colors=''.join(c['colors'] or []), pt=pt))
x = pd.DataFrame(rows)
x['btext'] = [bi.blind(t, nm, ty) for t, nm, ty in zip(x.text, x.name, x.type_line)]
x['auto'] = np.where(x.type_line.str.contains('Basic Land') | (x.btext.str.strip() == ''), 1, 0)
(HERE / 'label/input').mkdir(parents=True, exist_ok=True)
x.to_csv(HERE / 'label/cards.csv', index=False)
todo = x[x.auto == 0]
view = lambda r: f"#{r.id} | MV {r.mv} {r.colors or 'C'} | {r.type_line}" + (f" | {r.pt}" if r.pt else "") + "\n" + r.btext.replace("\n", " / ")
cards = [view(r) for r in todo.itertuples()]
for i in range(0, len(cards), 60):
    (HERE / 'label/input' / f'c{i // 60 + 1:02d}.txt').write_text('\n\n'.join(cards[i:i + 60]) + '\n')
print(len(x), 'cards', int(x.auto.sum()), 'auto', len(todo), 'to label')
