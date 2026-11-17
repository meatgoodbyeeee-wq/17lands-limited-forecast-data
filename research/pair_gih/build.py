"""Colour-pair card GIH: build the cell table (exploratory step 0).

One row per (set, card, pair): GIH games/wins in decks whose main colours are that pair (splash allowed),
from research/deck_pair/data/{SET}_cardpair.csv.gz (17Lands Public Game Data, first 28 days, Premier Draft, all users).
Joined with the B11g leave-one-set-out prediction of the card's overall GIH and the card's colours.
FRA is kept out of the exploration so it can be a clean held-out set later.

Usage: python3 research/pair_gih/build.py <oof_B11g.csv.gz> <colors.csv> <out.csv.gz>
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/deck_pair/data'
PAIRS = ["WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG"]
HOLDOUT = {"FRA"}


def main(oof_path, colors_path, out_path):
    oof = pd.read_csv(oof_path)
    col = pd.read_csv(colors_path, keep_default_na=False)
    # 17Lands names most double-faced cards by the front face (rooms keep "A // B"); the pool uses "front // back".
    # Add a front-face alias row; exact names win. Cards outside the B11g pool (some DFCs, bonus sheets) stay without pred.
    def alias(t):
        a = t[t['name'].str.contains(' // ')].copy()
        a['name'] = a['name'].str.split(' // ').str[0]
        return pd.concat([t, a]).drop_duplicates(['set', 'name'])
    oof, col = alias(oof), alias(col)
    rows = []
    for f in sorted(DATA.glob('*_cardpair.csv.gz')):
        s = f.name.split('_')[0]
        if s in HOLDOUT:
            continue
        cp = pd.read_csv(f)
        p = pd.read_csv(DATA / f'{s}_pairs.csv', keep_default_na=False)
        p = p[p['main_colors'].isin(PAIRS)].groupby('main_colors')[['games', 'wins']].sum()
        p['pair_wr'] = p['wins'] / p['games']
        two = p['games'].sum()
        set_wr = p['wins'].sum() / two  # mean WR of two-colour decks (splash allowed)
        gcols = [c for c in cp if c.endswith('_games')]
        cp['all_games'] = cp[gcols].sum(axis=1)
        cp['all_wins'] = cp[[c.replace('_games', '_wins') for c in gcols]].sum(axis=1)
        for pair in PAIRS:
            r = cp[['set', 'card_name', 'all_games', 'all_wins']].copy()
            r['pair'] = pair
            r['games'] = cp[f'{pair}_games']
            r['wins'] = cp[f'{pair}_wins']
            r['pair_wr'] = p.loc[pair, 'pair_wr']
            r['pair_share'] = p.loc[pair, 'games'] / two
            r['set_pair_wr'] = set_wr
            rows.append(r)
    d = pd.concat(rows, ignore_index=True).rename(columns={'card_name': 'name'})
    d = d.merge(oof[['set', 'name', 'rarity_ord', 'pred']], on=['set', 'name'], how='left')
    d = d.merge(col[['set', 'name', 'type_land', 'colors']], on=['set', 'name'], how='left')
    d['gih_pair'] = d['wins'] / d['games'].where(d['games'] > 0)
    d['gih_all'] = d['all_wins'] / d['all_games']
    d.to_csv(out_path, index=False)
    print(len(d), d['set'].nunique(), 'sets; cells with pred', d['pred'].notna().mean().round(3),
          '; with colours', d['colors'].notna().mean().round(3))


if __name__ == '__main__':
    main(*sys.argv[1:4])
