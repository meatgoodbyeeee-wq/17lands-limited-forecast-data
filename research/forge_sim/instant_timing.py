#!/usr/bin/env python3
"""When the AI casts instants (full Forge logs, `sim` without -q), by effect class and colour pair.

  python3 research/forge_sim/instant_timing.py --forge <forge checkout> <full log> [...] [--out <casts csv>]

Each instant cast from "Add To Stack: <deck> cast <card>" gets: whose turn (own / opponent's), phase (from "Phase:" lines),
whether the stack already held something (a response), and the card's effect class from its Forge script (first A:SP$ API;
removal = Destroy / DealDamage / ChangeZone / Debuff-style -X/-X Pump / Tap, pump = Pump / PumpAll on own, counter = Counter,
draw = Draw / Dig / ChangeZone from library, other).
"""
import argparse, re
from collections import defaultdict
from pathlib import Path
import pandas as pd

TURN = re.compile(r'^Turn: Turn (\d+) \((\S+)\)')
PHASE = re.compile(r"^Phase: (\S+)'s (.+?)(?: step| Step)?$")
CAST = re.compile(r'^Add To Stack: (\S+) cast (.+?)(?: targeting .*)?$')
RESOLVE = re.compile(r'^Resolve Stack: ')
ROUND = re.compile(r'^Round \d+ - (\S+)\[\d+\] vs (\S+)\[\d+\]')
GAMEEND = re.compile(r'^Game Result: ')


def card_info(forge, name, cache):
    if name in cache:
        return cache[name]
    f = Path(forge) / 'forge-gui/res/cardsfolder' / name[0].lower() / (re.sub(r'[^a-z0-9 ]', '', name.lower()).replace(' ', '_') + '.txt')
    types, api, text = '', '', ''
    if f.exists():
        lines = f.read_text(errors='ignore').splitlines()
        types = next((l for l in lines if l.startswith('Types:')), '')
        sp = next((l for l in lines if l.startswith('A:SP$')), '')
        api = sp.split('|')[0].replace('A:SP$', '').strip()
        text = sp
    if api in ('Destroy', 'DealDamage', 'DestroyAll', 'DamageAll', 'Tap', 'TapAll', 'Sacrifice', 'Fight') or \
            (api == 'ChangeZone' and 'Origin$ Battlefield' in text) or (api in ('Pump', 'PumpAll') and re.search(r'NumAtt\$ ?-', text)):
        cls = 'removal'
    elif api in ('Pump', 'PumpAll', 'Protection', 'ProtectionAll', 'PutCounter', 'PutCounterAll'):
        cls = 'pump'
    elif api == 'Counter':
        cls = 'counter'
    elif api in ('Draw', 'Dig', 'ChangeZone', 'Mill', 'Scry', 'Surveil'):
        cls = 'draw'
    else:
        cls = 'other'
    cache[name] = (types, api, cls)
    return cache[name]


def parse(forge, path, rows, cache):
    game, active, phase, stack, turn = 0, None, '', 0, 0
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.rstrip('\n')
        if ROUND.match(line) or GAMEEND.match(line):
            if ROUND.match(line):
                game += 1
            stack = 0; continue
        m = TURN.match(line)
        if m:
            turn, active = int(m.group(1)), m.group(2); stack = 0; continue
        m = PHASE.match(line)
        if m:
            phase = m.group(2); continue
        if RESOLVE.match(line):
            stack = max(0, stack - 1); continue
        m = CAST.match(line)
        if m:
            deck, name = m.group(1), m.group(2)
            types, api, cls = card_info(forge, name, cache)
            if 'Instant' in types:
                rows.append({'file': Path(path).name, 'game': game, 'turn': turn, 'deck': deck, 'pair': deck.split('_')[1], 'card': name,
                             'api': api, 'cls': cls, 'own_turn': deck == active, 'phase': phase, 'response': stack > 0})
            stack += 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--forge', required=True); ap.add_argument('logs', nargs='+'); ap.add_argument('--out')
    a = ap.parse_args()
    rows, cache = [], {}
    for p in a.logs:
        parse(a.forge, p, rows, cache)
    d = pd.DataFrame(rows)
    combat = d.phase.str.contains('Combat|Attackers|Blockers|Damage')
    d['when'] = 'own main'
    d.loc[d.own_turn & d.phase.isin(['Upkeep', 'Draw']), 'when'] = 'own upkeep/draw'
    d.loc[d.own_turn & combat, 'when'] = 'own combat'
    d.loc[d.own_turn & d.phase.str.contains('End|Cleanup'), 'when'] = 'own end'
    d.loc[~d.own_turn, 'when'] = 'opp other'
    d.loc[~d.own_turn & combat, 'when'] = 'opp combat'
    d.loc[~d.own_turn & d.phase.str.contains('End'), 'when'] = 'opp end'
    d.loc[~d.own_turn & d.phase.str.contains('Main'), 'when'] = 'opp main'
    print(f'instant casts: {len(d)} in {d.groupby("file").game.nunique().sum()} games')
    t = pd.crosstab(d.cls, d.when, margins=True)
    print(t.to_string())
    print((pd.crosstab(d.cls, d.when, normalize='index') * 100).round(0).to_string())
    print('response share by class:', (d.groupby('cls').response.mean() * 100).round(0).to_dict())
    print('opp-turn share by pair:', (d.groupby('pair').own_turn.apply(lambda s: (1 - s.mean()) * 100)).round(0).to_dict())
    c = d.groupby(['card', 'cls']).agg(n=('when', 'size'), opp_turn=('own_turn', lambda s: round((1 - s.mean()) * 100)),
                                       upkeep_draw=('when', lambda s: round((s == 'own upkeep/draw').mean() * 100)),
                                       own_main=('when', lambda s: round((s == 'own main').mean() * 100)),
                                       response=('response', lambda s: round(s.mean() * 100))).sort_values('n', ascending=False)
    print(c.head(40).to_string())
    if a.out:
        d.to_csv(a.out, index=False)


if __name__ == '__main__':
    main()
