#!/usr/bin/env python3
"""Forge self-play, step 2: best-of-one games between the fixed-rule decks (build_decks.py), results per game.

  python3 research/forge_sim/run_sim.py --forge <forge checkout> --decks research/forge_sim/decks_fra --out <games.csv>
         [--rounds 13] [--per-round 2] [--workers 3] [--mc off|on|max] [--ai Default] [--seed 1]

Each round is a round robin (Forge `sim -t RoundRobin -m 1`, best of one like Premier Draft) between a random subset of decks,
--per-round decks per colour pair (2 -> 20 decks, 190 games), so every pair meets the whole field evenly.
A game that reaches Forge's clock (-c, default 120 s) is recorded as a draw and left out of win rates.
--seen (needs the research hook in Forge's SimulateMatch, env FORGE_SIM_SEEN) also writes <out>_seen.csv: per game and player,
every own card that left the library (opening hand and draws) with its final zone, for card win rates when drawn (card_wr.py).
"""
import argparse, csv, os, random, re, shutil, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PAIRS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']
RES = re.compile(r'^Match Result: (\S+): (\d+) (\S+): (\d+)')
GAME = re.compile(r'^Game Result: Game \d+ ended in (\d+) ms\.')
SEEN = re.compile(r'^Seen: \d+\t(\S+)\t(play|draw)\t(\d+)\t(.*)$')


def run_round(a, jar, k):
    rng = random.Random(a.seed * 100003 + k)
    decks = sorted(Path(a.decks).glob('*.dck'))
    by = {p: [d for d in decks if f'_{p}_' in d.name] for p in PAIRS}
    pick = [d for p in PAIRS for d in rng.sample(by[p], a.per_round)]
    tmp = Path(tempfile.mkdtemp(prefix=f'fsim{k}_'))
    for d in pick:
        shutil.copy(d, tmp / d.name)
    cmd = ['java', '-Xmx2g', '-Djava.awt.headless=true', '-jar', str(jar), 'sim', '-D', str(tmp) + '/', '-m', '1', '-t', 'RoundRobin',
           '-q', '-s', str(a.seed * 1000 + k), '-c', str(a.clock), '-mc', a.mc]
    if a.ai:
        cmd += ['-a'] + [a.ai] * len(pick)
    env = dict(os.environ, FORGE_SIM_SEEN='1') if a.seen else None
    out = subprocess.run(cmd, cwd=Path(a.forge) / 'forge-gui', capture_output=True, text=True, timeout=6 * 3600, env=env).stdout.splitlines()
    shutil.rmtree(tmp, ignore_errors=True)
    rows, seen, pend, last = [], [], [], None
    for line in out:
        m = RES.match(line)
        if m:
            last = m.groups(); continue
        s = SEEN.match(line)
        if s:
            pend.append(s.groups()); continue
        g = GAME.match(line)
        if g and last:
            d1, w1, d2, w2 = last[0], int(last[1]), last[2], int(last[3])
            ms = int(g.group(1))
            draw = ms >= a.clock * 1000 - 50 or w1 == w2
            gid = f'{k}-{len(rows)}'
            for deck, order, turns, cards in pend:
                for c in cards.rstrip('|').split('|'):
                    if c:
                        name, zone = c.rsplit('@', 1)
                        seen.append({'game': gid, 'deck': deck, 'order': order, 'turns': int(turns), 'card': name, 'zone': zone})
            pend = []
            rows.append({'round': k, 'game': gid, 'deck1': d1, 'deck2': d2, 'pair1': d1.split('_')[1], 'pair2': d2.split('_')[1],
                         'winner': '' if draw else (d1 if w1 > w2 else d2), 'ms': ms, 'mc': a.mc, 'ai': a.ai or 'Default'})
            last = None
    return rows, seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--forge', required=True); ap.add_argument('--decks', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--rounds', type=int, default=13); ap.add_argument('--per-round', type=int, default=2)
    ap.add_argument('--workers', type=int, default=3); ap.add_argument('--mc', default='off'); ap.add_argument('--ai', default='')
    ap.add_argument('--seed', type=int, default=1); ap.add_argument('--clock', type=int, default=120)
    ap.add_argument('--seen', action='store_true'); ap.add_argument('--jar', help='Forge jar (default: the one built in --forge)')
    a = ap.parse_args()
    jar = Path(a.jar).resolve() if a.jar else \
        next((Path(a.forge) / 'forge-gui-desktop/target').glob('forge-gui-desktop-*-jar-with-dependencies.jar')).resolve()
    out = Path(a.out); new = not out.exists()
    sout = out.with_name(out.stem + '_seen.csv'); snew = not sout.exists()
    with open(out, 'a', newline='') as fh, open(sout, 'a', newline='') if a.seen else open(os.devnull, 'w') as sh, \
            ThreadPoolExecutor(a.workers) as ex:
        w = csv.DictWriter(fh, ['round', 'game', 'deck1', 'deck2', 'pair1', 'pair2', 'winner', 'ms', 'mc', 'ai'])
        sw = csv.DictWriter(sh, ['game', 'deck', 'order', 'turns', 'card', 'zone'])
        if new:
            w.writeheader()
        if a.seen and snew:
            sw.writeheader()
        for rows, seen in ex.map(lambda k: run_round(a, jar, k), range(a.rounds)):
            w.writerows(rows); fh.flush()
            if a.seen:
                sw.writerows(seen); sh.flush()
            print(f'round {rows[0]["round"] if rows else "?"}: {len(rows)} games', flush=True)


if __name__ == '__main__':
    main()
