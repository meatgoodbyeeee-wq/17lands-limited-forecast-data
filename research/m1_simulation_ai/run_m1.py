"""M1 runner (resumable). python3 run_m1.py <FORGE_DIR> <DECK_ROOT> <normal|hybrid> [--budget-min N] [jobs...]
Per job: stream raw log to disk -> parse -> m1_games/<mode>/job<j>.json (skipped if present) -> git add/commit/push (flock).
Games stopped as slow (120 s) are recorded with winner=None (Forge still prints a bogus winner). A job that hit OutOfMemory
or finished fewer games than expected is NOT marked complete (raw log kept as job<j>.incomplete.raw, not committed)."""
import sys, os, re, json, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:]]
BUDGET = 60
if '--budget-min' in args:
    i = args.index('--budget-min'); BUDGET = float(args[i + 1]); del args[i:i + 2]
FD, ROOT, MODE = args[0], args[1], args[2]
JOBS = [int(x) for x in args[3:] if x.isdigit()] or list(range(16))
assert MODE in ('normal', 'hybrid')
JAR = os.environ['FORGE_JAR']
OUT = f'{HERE}/m1_games/{MODE}'; os.makedirs(OUT, exist_ok=True)
HEAP = '1500m' if MODE == 'normal' else '2600m'
REPO = os.path.abspath(HERE + '/../..')

def parse(text):
    games, cur = [], []
    for l in text.split('\n'):
        cur.append(l)
        if l.startswith('Game Result'):
            m = re.search(r'ended in (\d+) ms\. (\S+) has won', l)
            ms = int(m.group(1)) if m else None; winner = m.group(2) if m else None
            slow = any(x.startswith('Stopping slow match') for x in cur) or (ms is not None and ms >= 120000)
            draws = {}
            for x in cur:
                if x.startswith('Information: K1_DREW '):
                    mm = re.match(r'Information: K1_DREW (\S+) drew (.+)$', x)
                    if mm: draws.setdefault(mm.group(1), set()).add(mm.group(2))
            games.append(dict(winner=None if slow else winner, slow=bool(slow), ms=ms, draws={k: sorted(v) for k, v in draws.items()}))
            cur = []
    return games

def commit(j):
    cmd = (f'cd {REPO} && flock /tmp/m1_git.lock sh -c "git add research/m1_simulation_ai/m1_games/{MODE}/job{j}.json && '
           f'git -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m \'M1: {MODE} job {j} games\n\n'
           f'Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01PVR8vpUzWG5PHBWGEkY1WV\' && '
           f'git push -q origin research/m1-simulation-ai"')
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print('commit job', j, 'rc', r.returncode, (r.stderr or '')[-200:], flush=True)

def run(j):
    out = f'{OUT}/job{j}.json'; raw = f'{OUT}/job{j}.raw'
    if os.path.exists(out): print('skip job', j, flush=True); return
    d = f'{ROOT}/job{j}'; nd = len([f for f in os.listdir(d) if f.endswith('.dck')]); expected = nd * (nd - 1) // 2
    env = dict(os.environ)
    if MODE == 'hybrid': env['FORGE_SIM_AI'] = 'hybrid'
    else: env.pop('FORGE_SIM_AI', None)
    cmd = ['java', f'-Xmx{HEAP}', '-jar', JAR, 'sim', '-t', 'roundrobin', '-D', d, '-m', '1', '-s', str(900 + j), '-c', '120']
    t0 = time.time()
    with open(raw, 'w') as fh:
        subprocess.run(cmd, cwd=FD + '/forge-gui', stdout=fh, stderr=subprocess.DEVNULL, timeout=6000, env=env)
    text = open(raw, errors='replace').read(); g = parse(text); oom = text.count('OutOfMemoryError')
    mins = (time.time() - t0) / 60
    slow = sum(x['slow'] for x in g)
    print(f'job {j} {MODE}: games {len(g)}/{expected} slow {slow} oom {oom} {mins:.1f} min', flush=True)
    if oom or len(g) < expected:
        os.replace(raw, f'{OUT}/job{j}.incomplete.raw'); print('INCOMPLETE job', j, flush=True); return
    json.dump(g, open(out, 'w')); os.remove(raw); commit(j)

t_start = time.time()
for j in JOBS:
    if (time.time() - t_start) / 60 > BUDGET: print('budget reached, stopping before job', j, flush=True); break
    try: run(j)
    except subprocess.TimeoutExpired: print('TIMEOUT job', j, flush=True)
    except Exception as e: print('FAIL job', j, repr(e), flush=True)
print('driver done', flush=True)
