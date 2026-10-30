#!/usr/bin/env python3
"""Forge self-play: compare raw `sim` outputs (FORGE_SIM_SEEN=1, BLOCK_AUDIT=1) of a few probe runs.

  python3 research/forge_sim/probe_fixes.py name=<sim stdout> [...]

Per run: games, AI decisions cut short by the time limit, block audit (attackers faced, share blocked, attackers left unblocked
although a block that kills it and survives / survives / trades with a less valuable creature / trades evenly was available),
share of drawn spells held in hand to the end, and held share for the cards the fixes target.
"""
import re, sys
from collections import Counter

TARGETS = ['Ferocity of the Hunt', 'Artifist Acumen', 'Countersculpt', 'Icy Reception', 'Sphinx\'s Approach', 'Command the Stage']
BASICS = {'Plains', 'Island', 'Swamp', 'Mountain', 'Forest'}


def main():
    for arg in sys.argv[1:]:
        name, path = arg.split('=', 1)
        games = timeouts = 0
        blk = Counter()
        drawn, held = Counter(), Counter()
        for line in open(path, errors='ignore'):
            line = line.rstrip('\n')
            if line.startswith('Game Result:'):
                games += 1
            elif line.startswith('Timeouts:'):
                timeouts += int(line.split('\t')[1])
            elif line.startswith('BlockAudit:'):
                f = line.split('\t')
                for k, v in zip(['attackers', 'blocked', 'safe_kill', 'safe', 'fav_trade', 'trade'], f[3:]):
                    blk[k] += int(v)
            elif line.startswith('Seen:'):
                for c in line.split('\t')[4].rstrip('|').split('|'):
                    if c and c.rsplit('@', 1)[0] not in BASICS:
                        n, z = c.rsplit('@', 1)
                        drawn[n] += 1; held[n] += z == 'Hand'
        a = blk['attackers'] or 1
        print(f'== {name}: {games} games, timeouts {timeouts} ({timeouts / max(games, 1):.2f}/game)')
        print(f'   attackers faced {blk["attackers"]}, blocked {blk["blocked"] / a:.1%}; left unblocked although available: '
              f'kill-and-survive {blk["safe_kill"] / a:.1%}, survive {blk["safe"] / a:.1%}, '
              f'favourable trade {blk["fav_trade"] / a:.1%}, even trade {blk["trade"] / a:.1%}')
        print(f'   drawn spells held to the end {sum(held.values()) / max(sum(drawn.values()), 1):.1%}')
        print('   held: ' + ', '.join(f'{t} {held[t]}/{drawn[t]}' for t in TARGETS))


if __name__ == '__main__':
    main()
