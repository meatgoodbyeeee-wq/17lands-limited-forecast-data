#!/usr/bin/env python3
"""Forge self-play, step 4: card win rates when drawn, against 17Lands GIH WR (which cards the AI plays badly).

  python3 research/forge_sim/card_wr.py research/forge_sim/runs/<games>.csv [--gih research/fra_check/fra_actual_gih500.csv]
         [--min-games 150] [--out <cards.csv>]

Reads <games>.csv and <games>_seen.csv or .csv.gz (run_sim.py --seen). Per card (basics left out), over decided games:
  sim_gih  win rate of the player-games where at least one copy left the library (opening hand or drawn; mill counts too)
  sim_gns  win rate of the player-games where the card was in the deck but not drawn
  sim_iwd  sim_gih - sim_gns (within the same decks, so the deck and colour-pair strength cancel)
  held     share of drawn copies still in hand at the end of the game (never cast)
Agreement: Spearman of sim_gih and of sim_iwd with 17Lands GIH WR. The gap (17Lands GIH rank minus sim_iwd rank, percentiles)
ranks the cards the AI gets least out of compared with human players.
"""
import argparse, glob, os, re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

BASICS = {'Plains', 'Island', 'Swamp', 'Mountain', 'Forest'}


def deck_lists(deck_dir):
    rows = []
    for f in glob.glob(str(Path(deck_dir) / '*.dck')):
        for line in open(f):
            m = re.match(r'(\d+) (.+)\|FRA', line.strip())
            if m and m.group(2) not in BASICS:
                rows.append((os.path.basename(f)[:-4], m.group(2)))
    return pd.DataFrame(rows, columns=['deck', 'card']).drop_duplicates()


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument('games')
    ap.add_argument('--gih', default=str(here.parent / 'fra_check/fra_actual_gih500.csv'))
    ap.add_argument('--decks', default=str(here / 'decks_fra'))
    ap.add_argument('--min-games', type=int, default=150)
    ap.add_argument('--out')
    a = ap.parse_args()
    games = pd.read_csv(a.games)
    sp = Path(a.games).with_name(Path(a.games).stem + '_seen.csv')
    seen = pd.read_csv(sp if sp.exists() else sp.with_name(sp.name + '.gz'))
    games = games[games.winner.notna() & (games.winner != '')]
    pg = pd.concat([games.assign(deck=games.deck1), games.assign(deck=games.deck2)])
    pg['win'] = (pg.winner == pg.deck).astype(int)
    pg = pg[['game', 'deck', 'win']]

    seen = seen[~seen.card.isin(BASICS)]
    drawn = seen.groupby(['game', 'deck', 'card']).agg(copies=('zone', 'size'), held=('zone', lambda z: (z == 'Hand').sum())).reset_index()
    full = pg.merge(deck_lists(a.decks), on='deck').merge(drawn, on=['game', 'deck', 'card'], how='left')
    full['drawn'] = full.copies.notna()
    g = full.groupby('card')
    t = pd.DataFrame({
        'decks': g.deck.nunique(),
        'gih_games': g.drawn.sum(),
        'sim_gih': full[full.drawn].groupby('card').win.mean() * 100,
        'sim_gns': full[~full.drawn].groupby('card').win.mean() * 100,
        'held': g.held.sum() / g.copies.sum() * 100,
    })
    t['sim_iwd'] = t.sim_gih - t.sim_gns
    act = pd.read_csv(a.gih).set_index('name').rename(columns={'gih': 'actual_gih', 'gih_n': 'actual_gih_n'})
    t = t.join(act, how='inner')
    t = t[t.gih_games >= a.min_games].copy()
    t['gap'] = t.actual_gih.rank(pct=True) - t.sim_iwd.rank(pct=True)

    def rho(x):
        r = spearmanr(t[x], t.actual_gih)
        return f'{r.statistic:+.2f} (p={r.pvalue:.3f})'

    print(f'{len(games)} decided games, {len(t)} cards with >= {a.min_games} games drawn')
    print(f'Spearman with 17Lands GIH WR: sim_gih {rho("sim_gih")}, sim_iwd {rho("sim_iwd")}')
    print(f'Spearman held vs 17Lands GIH WR: {rho("held")}; mean held {t.held.mean():.1f}%')
    cols = ['decks', 'gih_games', 'sim_gih', 'sim_iwd', 'held', 'actual_gih']
    pd.set_option('display.width', 200)
    print('\nAI gets least out of (17Lands rank high, sim IWD rank low):')
    print(t.sort_values('gap', ascending=False).head(20)[cols].round(1).to_string())
    print('\nAI gets most out of:')
    print(t.sort_values('gap').head(10)[cols].round(1).to_string())
    print('\nMost often held in hand:')
    print(t.sort_values('held', ascending=False).head(15)[cols].round(1).to_string())
    if a.out:
        t.sort_values('gap', ascending=False).round(2).to_csv(a.out, index_label='card')


if __name__ == '__main__':
    main()
