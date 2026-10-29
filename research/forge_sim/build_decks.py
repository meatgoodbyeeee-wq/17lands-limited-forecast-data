#!/usr/bin/env python3
"""Forge self-play, step 1: fixed-rule decks per colour pair (FRA first; user request 2026-10-29).

  python3 research/forge_sim/build_decks.py --cards <pages>/data/target.json.gz --out research/forge_sim/decks_fra [--per-pair 10]

Rule (fixed before any game is played):
- Eligible cards for pair XY: non-land cards whose colours are a subset of {X, Y} (colourless included).
- Pool: 45 picks with replacement, each card weighted by its expected copies per play booster
  (common 6.75 / #commons, uncommon 5.14 / #uncommons, rare 0.85 / #rares, mythic 0.15 / #mythics; FRA booster sheet),
  at most 4 copies of a card. So decks are mostly commons and uncommons.
- Deck: the 23 best spells of the pool by the frozen B10 card prediction (research/c9_power_questions/fra_frozen_predictions.csv),
  greedy with at most 9 non-creature spells and at most 4 cards of mana value >= 5 (then filled by prediction if short),
  plus 17 basic lands split by the coloured mana symbols of the 23 spells (at least 6 of each colour).
- Seeds: SEED + pair index * 100 + deck number; per pair 10 decks.
"""
import argparse, gzip, json, re
from pathlib import Path
import numpy as np, pandas as pd

PAIRS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']
BASIC = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}
PER_PACK = {'common': 6.75, 'uncommon': 5.14, 'rare': 0.85, 'mythic': 0.15}
SEED = 20261029
R = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cards', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--per-pair', type=int, default=10)
    ap.add_argument('--set', default='FRA')
    a = ap.parse_args()
    cards = json.loads(gzip.open(a.cards, 'rt', encoding='utf-8').read())['cards']
    pred = pd.read_csv(R / 'c9_power_questions/fra_frozen_predictions.csv').set_index('id')['pred_B10']
    d = pd.DataFrame([{'id': c['id'], 'name': c['name'], 'rarity': c['rarity'], 'colors': ''.join(c['colors']),
                       'cmc': float(c['cmc'] or 0), 'mana_cost': c.get('mana_cost') or '', 'type_line': c['type_line']} for c in cards])
    d = d[~d.type_line.str.contains('Land') & d.rarity.isin(PER_PACK)].copy()
    d['pred'] = d.id.map(pred); assert d.pred.notna().all()
    n = d.rarity.value_counts()
    d['w'] = d.rarity.map(lambda r: PER_PACK[r] / n[r])
    d['creature'] = d.type_line.str.contains('Creature')
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for pi, pair in enumerate(PAIRS):
        e = d[d.colors.apply(lambda c: set(c) <= set(pair))].reset_index(drop=True)
        for k in range(a.per_pair):
            rng = np.random.default_rng(SEED + pi * 100 + k)
            pool = pd.Series(rng.choice(len(e), 45, p=(e.w / e.w.sum()).to_numpy())).value_counts().clip(upper=4)
            p = e.loc[pool.index].assign(n=pool.values).sort_values('pred', ascending=False)
            deck, nc, big = [], 0, 0
            for r in p.itertuples():
                for _ in range(r.n):
                    if len(deck) == 23: break
                    if (not r.creature and nc >= 9) or (r.cmc >= 5 and big >= 4): break
                    deck.append(r); nc += not r.creature; big += r.cmc >= 5
            rest = [r for r in p.itertuples() for _ in range(r.n)]
            for r in rest:
                if len(deck) == 23: break
                if sum(x.name == r.name for x in deck) < sum(1 for y in rest if y.name == r.name): deck.append(r)
            assert len(deck) == 23, (pair, k, len(deck))
            sym = {c: sum(len(re.findall(r'\{[^}]*' + c + r'[^}]*\}', x.mana_cost)) for x in deck) for c in pair}
            tot = max(1, sum(sym.values()))
            l0 = min(11, max(6, round(17 * sym[pair[0]] / tot))); lands = {pair[0]: l0, pair[1]: 17 - l0}
            cnt = pd.Series([x.name for x in deck]).value_counts()
            name = f'{a.set}_{pair}_{k:02d}'
            lines = ['[metadata]', f'Name={name}', '[main]'] + [f'{v} {nm}|{a.set}' for nm, v in cnt.items()] + \
                    [f'{v} {BASIC[c]}' for c, v in lands.items()]
            (a.out / f'{name}.dck').write_text('\n'.join(lines) + '\n')
            rows.append({'deck': name, 'pair': pair, 'creatures': int(sum(x.creature for x in deck)),
                         'C': int(sum(x.rarity == 'common' for x in deck)), 'U': int(sum(x.rarity == 'uncommon' for x in deck)),
                         'RM': int(sum(x.rarity in ('rare', 'mythic') for x in deck)), 'mean_pred_pp': float(np.mean([x.pred for x in deck]) * 100),
                         **{f'land_{c}': v for c, v in lands.items()}})
    s = pd.DataFrame(rows); s.to_csv(a.out / 'decks.csv', index=False)
    print(s.groupby('pair')[['creatures', 'C', 'U', 'RM', 'mean_pred_pp']].mean().round(2).to_string())


if __name__ == '__main__':
    main()
