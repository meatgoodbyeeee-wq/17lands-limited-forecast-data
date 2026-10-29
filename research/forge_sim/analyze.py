#!/usr/bin/env python3
"""Forge self-play, step 3: colour-pair win rates from the games and their agreement with 17Lands.

  python3 research/forge_sim/analyze.py research/forge_sim/runs/<games>.csv [--actual research/fra_check/fra-actual-color-ratings.json]

Pair win rate = wins / decided games of that pair's decks against other pairs (mirror games and draws left out).
Agreement: Spearman over the 10 pairs with the centred 17Lands Color Ratings win rate (FRA: 28 days, non-splash two-colour),
with a 95% interval from resampling rounds (bootstrap, 2000 draws).
"""
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

PAIRS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']


def pair_wr(g):
    g = g[(g.pair1 != g.pair2) & (g.winner != '')]
    rows = []
    for p in PAIRS:
        s = g[(g.pair1 == p) | (g.pair2 == p)]
        wins = (s.winner.str.split('_').str[1] == p).sum()
        rows.append({'pair': p, 'games': len(s), 'wins': int(wins), 'wr': wins / len(s) * 100 if len(s) else np.nan})
    return pd.DataFrame(rows).set_index('pair')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('games')
    ap.add_argument('--actual', default=str(Path(__file__).resolve().parents[1] / 'fra_check/fra-actual-color-ratings.json'))
    a = ap.parse_args()
    g = pd.read_csv(a.games, keep_default_na=False)
    cr = json.loads(Path(a.actual).read_text())
    y = pd.Series({k: v['wr_pct'] for k, v in cr['pairs'].items()}).loc[PAIRS]; y = y - y.mean()
    t = pair_wr(g)
    t['sim_centred'] = t.wr - t.wr.mean(); t['actual_centred'] = y
    t['sim_rank'] = t.wr.rank(ascending=False).astype(int); t['actual_rank'] = y.rank(ascending=False).astype(int)
    rho = spearmanr(t.wr, y).correlation
    rng = np.random.default_rng(1); rounds = g['round'].unique(); bs = []
    for _ in range(2000):
        s = pd.concat([g[g['round'] == r] for r in rng.choice(rounds, len(rounds))])
        bs.append(spearmanr(pair_wr(s).wr, y).correlation)
    n = int(((g.pair1 != g.pair2) & (g.winner != '')).sum())
    print(t.round(2).to_string())
    print(json.dumps({'games': len(g), 'decided_cross_pair_games': n, 'draws': int((g.winner == '').sum()),
                      'mean_game_s': round(g.ms.mean() / 1000, 2), 'spearman_vs_17lands': round(rho, 3),
                      'spearman_95ci': [round(float(np.nanpercentile(bs, 2.5)), 3), round(float(np.nanpercentile(bs, 97.5)), 3)],
                      'sim_sd_pp': round(float(t.wr.std()), 2), 'actual_sd_pp': round(float(y.std()), 2)}, indent=1))


if __name__ == '__main__':
    main()
