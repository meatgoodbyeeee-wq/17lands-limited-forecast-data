"""J2d: per-game records. python3 rune.py <FORGE_DIR> [smoke]"""
import sys, os, re, json, subprocess, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = HERE + '/games'; FD = sys.argv[1]; SMOKE = len(sys.argv) > 2
def parse(text):
    games, cur = [], []
    for l in text.split('\n'):
        cur.append(l)
        if l.startswith('Game Result'):
            turn = 0; casts = []; win1 = 'Ai(1)-' in l.split('has won')[0] if 'has won' in l else None
            for x in cur:
                if x.startswith('Turn:'):
                    m = re.search(r'Turn (\d+)', x); turn = max(turn, int(m.group(1))) if m else turn
                if x.startswith('Add To Stack: Ai(1)-') and ' cast Avengers Assemble' in x: casts.append(lastturn(cur, x))
            draws = [lastturn(cur, x) for x in cur if x.startswith('Information: J2D_DREW Ai(1)-')]
            games.append(dict(turns=turn, win1=win1, ncast=len(casts), first_cast=min(casts) if casts else None, ndrew=len(draws), first_draw=min(draws) if draws else None)); cur = []
    return games
def lastturn(cur, line):
    t = 0
    for x in cur:
        if x is line: break
        if x.startswith('Turn:'):
            m = re.search(r'Turn (\d+)', x); t = int(m.group(1)) if m else t
    return t
def job(j):
    jid, a, b, seed = j; out = f'{OUT}/{jid}.json'
    if os.path.exists(out): return jid
    n = '4' if SMOKE else '100'
    cmd = ['java', '-Xmx1g', '-jar', FD + '/forge-gui-desktop/target/forge-gui-desktop-2.0.16-SNAPSHOT-jar-with-dependencies.jar', 'sim', '-d', a, b, '-n', n, '-s', str(seed), '-c', '120']
    t = subprocess.run(cmd, cwd=FD + '/forge-gui', capture_output=True, text=True, timeout=3600).stdout
    g = parse(t)
    if len(g) != int(n): raise RuntimeError(f'{jid}: {len(g)} games parsed')
    json.dump(g, open(out, 'w')); return jid
decks = ['V'] + [f'B{k}c' for k in (1, 2, 3)] + [f'V2_{k}' for k in (1, 2, 3)] + [f'V1_{k}' for k in (1, 2, 3)]
jobs = [(f'{d}_{o}', f'j2_{d}.dck', f'j2_opp{o}.dck', 2000 + o) for d in decks for o in range(4)]
if SMOKE: jobs = [('smoke_V_0', 'j2_V.dck', 'j2_opp0.dck', 2000)]
with cf.ThreadPoolExecutor(2) as ex:
    for f in cf.as_completed([ex.submit(job, j) for j in jobs]):
        try: print('done', f.result(), flush=True)
        except Exception as e: print('FAIL', e, flush=True)
