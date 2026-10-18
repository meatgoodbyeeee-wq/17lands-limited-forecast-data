import sys, os, re, json, subprocess, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); RES = HERE + '/results'; os.makedirs(RES, exist_ok=True)
FD = sys.argv[1]
def job(j):
    jid, a, b, seed = j; out = f'{RES}/{jid}.json'
    if os.path.exists(out): return jid
    cmd = ['java', '-Xmx1g', '-jar', FD + '/forge-gui-desktop/target/forge-gui-desktop-2.0.16-SNAPSHOT-jar-with-dependencies.jar', 'sim', '-d', a, b, '-n', '100', '-s', str(seed), '-q', '-c', '120']
    t = subprocess.run(cmd, cwd=FD + '/forge-gui', capture_output=True, text=True, timeout=3600).stdout
    m = re.findall(r'Match Result: Ai\(1\)-[^:]+: (\d+) Ai\(2\)-[^:]+: (\d+)', t)
    if not m: raise RuntimeError(jid)
    w, l = map(int, m[-1]); json.dump(dict(w=w, l=l), open(out, 'w')); return jid
jobs = [(f'{x}_{k}', f'j2_{x}.dck', f'j2_opp{k}.dck', 2000 + k) for x in ('B1','B2','B3') for k in range(4)]
with cf.ThreadPoolExecutor(2) as ex:
    for f in cf.as_completed([ex.submit(job, j) for j in jobs]):
        try: print('done', f.result(), flush=True)
        except Exception as e: print('FAIL', e, flush=True)
