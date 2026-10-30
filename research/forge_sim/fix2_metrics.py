#!/usr/bin/env python3
"""Main run of PLAN_fixes2.md (B, F, A): the pre-registered pair and side metrics.

  python3 research/forge_sim/fix2_metrics.py B=runs/fix2_B.csv F=runs/fix2_F.csv A=runs/fix2_A.csv [--diff F-B --diff A-F]

Per condition: pair Spearman vs 17Lands splash combined with a 95% interval from resampling rounds; drawn spells held to the end
and the held share of the target cards; block audit; share of games of 12 turns or fewer and the blue pairs' win rate in them.
Differences (--diff X-Y) resample the same rounds for both runs (same seed, so the same pairings).
"""
import argparse
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from analyze import PAIRS, pair_wr, actual_pairs

HERE = Path(__file__).resolve().parent
TARGETS = ['Ferocity of the Hunt', 'Artifist Acumen', 'Countersculpt']
BASICS = {'Plains', 'Island', 'Swamp', 'Mountain', 'Forest'}
BLUE = {'WU', 'UB', 'UR', 'UG'}


def rho(g, y):
    return spearmanr(pair_wr(g).wr.loc[PAIRS], y).statistic


def load(path):
    g = pd.read_csv(path, keep_default_na=False)
    sp = Path(path).with_name(Path(path).stem + '_seen.csv')
    s = pd.read_csv(sp if sp.exists() else sp.with_name(sp.name + '.gz'), keep_default_na=False)
    return g, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('runs', nargs='+'); ap.add_argument('--diff', action='append', default=[])
    ap.add_argument('--boot', type=int, default=2000)
    a = ap.parse_args()
    y = actual_pairs(HERE / 'actual/fra-color-ratings-splash-combined.json').loc[PAIRS]
    runs = {k: load(v) for k, v in (r.split('=', 1) for r in a.runs)}
    rng = np.random.default_rng(0)
    rounds = sorted(next(iter(runs.values()))[0]['round'].unique())
    draws = [rng.choice(rounds, len(rounds)) for _ in range(a.boot)]

    def boot(g):
        by = {r: d for r, d in g.groupby('round')}
        return np.array([rho(pd.concat([by[r] for r in d]), y) for d in draws])

    bs = {}
    for k, (g, s) in runs.items():
        bs[k] = boot(g)
        lo, hi = np.percentile(bs[k], [2.5, 97.5])
        cards = s[(s.zone != 'BlockAudit') & ~s.card.isin(BASICS)]
        held = (cards.zone == 'Hand').mean() * 100
        tg = ', '.join(f'{t} {(c.zone == "Hand").sum()}/{len(c)}' for t in TARGETS for c in [cards[cards.card == t]])
        b = s[s.zone == 'BlockAudit'].card.str.split('|', expand=True).astype(int).sum()
        turns = s[s.zone != 'BlockAudit'].groupby('game').turns.max()
        gg = g[g.winner != ''].assign(turns=lambda d: d.game.map(turns))
        short = gg[gg.turns <= 12]
        bw = sum(((short.pair1 == p) | (short.pair2 == p)).sum() for p in BLUE)
        bwins = sum((short.winner.str.split('_').str[1] == p).sum() for p in BLUE)
        bmirror = sum(((short.pair1 == p) & (short.pair2 == p)).sum() for p in BLUE)
        print(f'== {k}: {len(g)} games, draws {(g.winner == "").sum()}, timeouts {pd.to_numeric(g.timeouts, errors="coerce").sum():.0f}, '
              f'mean turns {turns.mean():.2f}')
        print(f'   pair Spearman {rho(g, y):+.2f} (95% {lo:+.2f}..{hi:+.2f}); drawn spells held {held:.1f}%; held: {tg}')
        print(f'   blocks: faced {b[0]}, blocked {b[1] / b[0]:.1%}; missed kill-and-survive {b[2] / b[0]:.2%}, survive {b[3] / b[0]:.2%}, '
              f'trade with a less valuable creature {b[4] / b[0]:.2%}, even trade {b[5] / b[0]:.2%}')
        print(f'   games <= 12 turns {len(short) / len(gg):.1%}; blue pairs win {bwins / max(bw, 1):.1%} of their {bw} seats in them '
              f'(mirror games count both seats: {bmirror})')
    for d in a.diff:
        x, z = d.split('-')
        diff = bs[x] - bs[z]
        lo, hi = np.percentile(diff, [2.5, 97.5])
        print(f'diff {d}: {rho(runs[x][0], y) - rho(runs[z][0], y):+.2f} (95% {lo:+.2f}..{hi:+.2f})')


if __name__ == '__main__':
    main()
