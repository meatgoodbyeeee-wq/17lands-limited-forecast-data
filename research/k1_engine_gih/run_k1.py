"""python3 run_k1.py <FORGE_DIR> <DECK_ROOT> [jobs...]; per-job summary -> k1_games/job<j>.json"""
import sys, os, re, json, subprocess, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.environ.get('K1_OUT', HERE + '/k1_games'); os.makedirs(OUT, exist_ok=True)
FD, ROOT = sys.argv[1], sys.argv[2]; JOBS = [int(x) for x in sys.argv[3:]] or list(range(8)); JAR = os.environ.get('FORGE_JAR')
def parse(text):
    games, cur = [], []
    for l in text.split('\n'):
        cur.append(l)
        if l.startswith('Game Result'):
            m = re.search(r'ended in \d+ ms\. (\S+) has won', l); winner = m.group(1) if m else None
            draws = {}
            for x in cur:
                if x.startswith('Information: K1_DREW '):
                    m = re.match(r'Information: K1_DREW (\S+) drew (.+)$', x)
                    if m: draws.setdefault(m.group(1), set()).add(m.group(2))
            games.append(dict(winner=winner, draws={k: sorted(v) for k, v in draws.items()})); cur = []
    return games
def job(j):
    out = f'{OUT}/job{j}.json'
    if os.path.exists(out): return j
    cmd = ['java', '-Xmx1500m', '-jar', JAR, 'sim', '-t', 'roundrobin', '-D', f'{ROOT}/job{j}', '-m', '1', '-s', str(900 + j), '-c', '120']
    t = subprocess.run(cmd, cwd=FD + '/forge-gui', capture_output=True, text=True, timeout=7200).stdout
    g = parse(t); json.dump(g, open(out, 'w'))
    if not g: open(out + '.err', 'w').write(t[-3000:]); raise RuntimeError(f'job{j}: no games parsed')
    return j
with cf.ThreadPoolExecutor(2) as ex:
    for f in cf.as_completed([ex.submit(job, j) for j in JOBS]):
        try: print('done job', f.result(), flush=True)
        except Exception as e: print('FAIL', e, flush=True)
