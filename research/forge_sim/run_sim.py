#!/usr/bin/env python3
"""Forge self-play, step 2: best-of-one games between the fixed-rule decks (build_decks.py), results per game.

  python3 research/forge_sim/run_sim.py --forge <forge checkout> --decks research/forge_sim/decks_fra --out <games.csv>
         [--rounds 13] [--per-round 2] [--workers 3] [--mc off|on|max] [--ai Default] [--seed 1]

Each round is a round robin (Forge `sim -t RoundRobin -m 1`, best of one like Premier Draft) between a random subset of decks,
--per-round decks per colour pair (2 -> 20 decks, 190 games), so every pair meets the whole field evenly.
A game that reaches Forge's clock (-c, default 120 s) is recorded as a draw and left out of win rates.
"""
import argparse, csv, random, re, shutil, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PAIRS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']
RES = re.compile(r'^Match Result: (\S+): (\d+) (\S+): (\d+)')
GAME = re.compile(r'^Game Result: Game \d+ ended in (\d+) ms\.')


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
    out = subprocess.run(cmd, cwd=Path(a.forge) / 'forge-gui', capture_output=True, text=True, timeout=6 * 3600).stdout.splitlines()
    shutil.rmtree(tmp, ignore_errors=True)
    rows, last = [], None
    for line in out:
        m = RES.match(line)
        if m:
            last = m.groups(); continue
        g = GAME.match(line)
        if g and last:
            d1, w1, d2, w2 = last[0], int(last[1]), last[2], int(last[3])
            ms = int(g.group(1))
            draw = ms >= a.clock * 1000 - 50 or w1 == w2
            rows.append({'round': k, 'deck1': d1, 'deck2': d2, 'pair1': d1.split('_')[1], 'pair2': d2.split('_')[1],
                         'winner': '' if draw else (d1 if w1 > w2 else d2), 'ms': ms, 'mc': a.mc, 'ai': a.ai or 'Default'})
            last = None
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--forge', required=True); ap.add_argument('--decks', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--rounds', type=int, default=13); ap.add_argument('--per-round', type=int, default=2)
    ap.add_argument('--workers', type=int, default=3); ap.add_argument('--mc', default='off'); ap.add_argument('--ai', default='')
    ap.add_argument('--seed', type=int, default=1); ap.add_argument('--clock', type=int, default=120)
    a = ap.parse_args()
    jar = next((Path(a.forge) / 'forge-gui-desktop/target').glob('forge-gui-desktop-*-jar-with-dependencies.jar')).resolve()
    out = Path(a.out); new = not out.exists()
    with open(out, 'a', newline='') as fh, ThreadPoolExecutor(a.workers) as ex:
        w = csv.DictWriter(fh, ['round', 'deck1', 'deck2', 'pair1', 'pair2', 'winner', 'ms', 'mc', 'ai'])
        if new:
            w.writeheader()
        for rows in ex.map(lambda k: run_round(a, jar, k), range(a.rounds)):
            w.writerows(rows); fh.flush()
            print(f'round {rows[0]["round"] if rows else "?"}: {len(rows)} games', flush=True)


if __name__ == '__main__':
    main()
