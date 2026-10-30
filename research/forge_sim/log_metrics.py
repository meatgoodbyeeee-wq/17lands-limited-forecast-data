#!/usr/bin/env python3
"""Forge self-play: play metrics from full game logs (Forge `sim` without -q), per deck.

  python3 research/forge_sim/log_metrics.py <full log> [...] [--out <per-turn csv>]

Per player turn cycle (own untap to own next untap): lands on the battlefield, lands tapped for mana (own turn and the opponent's
following turn), spells cast on own turn and on the opponent's turn, attackers declared. Only lands are counted for mana (land
card ids come from "Land: <player> played <name> (<id>)"); mana from creatures and artifacts is left out.
Use: mana use = tapped / lands, by colour pair and turn number, to see whether a deck leaves mana unused (e.g. held for instants).
"""
import argparse, re
from collections import defaultdict
import pandas as pd

TURN = re.compile(r'^Turn: Turn (\d+) \((\S+)\)')
LAND = re.compile(r'^Land: (\S+) played .+ \((\d+)\)$')
MANA = re.compile(r'^Mana: .+ \((\d+)\) - ')
CAST = re.compile(r'^Add To Stack: (\S+) cast (.+?)(?: targeting .*)?$')
ATTACK = re.compile(r'^Combat: (\S+) assigned (.+) to attack')
RESULT = re.compile(r'^Game Result: Game \d+ ended in \d+ ms\. (\S+) has won')
ROUND = re.compile(r'^Round \d+ - (\S+)\[\d+\] vs (\S+)\[\d+\]')


def parse(path, rows):
    game, players, owner, lands, cur, winner_rows = 0, None, {}, defaultdict(int), {}, []
    active = None
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.rstrip('\n')
        m = ROUND.match(line)
        if m:
            game += 1; players = (m.group(1), m.group(2)); owner, lands, cur, active = {}, defaultdict(int), {}, None
            continue
        m = TURN.match(line)
        if m:
            active = m.group(2)
            if active in cur:
                rows.append(cur.pop(active))
            cur[active] = {'file': path, 'game': game, 'deck': active, 'turn': int(m.group(1)), 'lands': lands[active],
                           'tapped': 0, 'cast_own': 0, 'cast_opp': 0, 'attacks': 0}
            continue
        if players is None or active is None:
            continue
        m = LAND.match(line)
        if m:
            owner[m.group(2)] = m.group(1); lands[m.group(1)] += 1
            if m.group(1) in cur:
                cur[m.group(1)]['lands'] += 1
            continue
        m = MANA.match(line)
        if m and m.group(1) in owner and owner[m.group(1)] in cur:
            cur[owner[m.group(1)]]['tapped'] += 1
            continue
        m = CAST.match(line)
        if m and m.group(1) in cur:
            cur[m.group(1)]['cast_own' if m.group(1) == active else 'cast_opp'] += 1
            continue
        m = ATTACK.match(line)
        if m and m.group(1) in cur:
            cur[m.group(1)]['attacks'] += 1
            continue
        m = RESULT.match(line)
        if m:
            for r in cur.values():
                rows.append(r)
            cur = {}
            for r in rows:
                if r['file'] == path and r['game'] == game:
                    r['win'] = int(r['deck'] == m.group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('logs', nargs='+'); ap.add_argument('--out')
    a = ap.parse_args()
    rows = []
    for f in a.logs:
        parse(f, rows)
    t = pd.DataFrame(rows).dropna(subset=['win'])
    t['pair'] = t.deck.str.split('_').str[1]
    t['own_turn'] = (t.turn + 1) // 2
    t = t[t.lands > 0]
    t['use'] = (t.tapped / t.lands).clip(upper=1)
    pd.set_option('display.width', 200)
    print(f'{t.game.nunique()} games per file, {len(t)} player turns')
    print('\nMana use (lands tapped / lands), by own turn number:')
    print(t[t.own_turn <= 10].pivot_table(index='pair', columns='own_turn', values='use', aggfunc='mean').round(2).to_string())
    print('\nPer player turn, turns 3-10:')
    s = t[(t.own_turn >= 3) & (t.own_turn <= 10)]
    print(s.groupby('pair')[['use', 'cast_own', 'cast_opp', 'attacks']].mean().round(2).to_string())
    if a.out:
        t.to_csv(a.out, index=False)


if __name__ == '__main__':
    main()
