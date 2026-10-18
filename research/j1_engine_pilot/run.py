"""J1 stage 0 driver. Resumable: results/<job>.json are skipped when present.
  python3 run.py select | python3 run.py run <FORGE_DIR> | python3 run.py report
"""
import sys, os, re, json, random, hashlib, unicodedata, subprocess, concurrent.futures as cf
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen
HERE = os.path.dirname(os.path.abspath(__file__)); RES = HERE + '/results'; os.makedirs(RES, exist_ok=True)
DECKS = '/root/.forge/decks/constructed'; SET = 'MKM'; NOPP = 4; NG = 100
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
def forge_names(fd): 
    out = set()
    for r, _, fs in os.walk(fd + '/forge-gui/res/cardsfolder'):
        out |= {norm(f[:-4]) for f in fs if f.endswith('.txt')}
    return out
def pair_for(name, colors):
    c = [x for x in 'WUBRG' if x in colors]
    if len(c) == 2: return ''.join(c)
    rest = [x for x in 'WUBRG' if x not in c]
    return ''.join(sorted([c[0], rest[int(hashlib.md5(name.encode()).hexdigest(), 16) % 4]], key='WUBRG'.index)) if c else 'WU'
def select(fd):
    o = pd.read_csv(HERE + '/../c9_power_questions/oof_B10.csv.gz'); o = o[o.set == SET]
    p = gen.pool(SET).set_index('name'); fn = forge_names(fd)
    rows = []
    for _, r in o.iterrows():
        if r['name'] not in p.index: continue
        q = p.loc[r['name']]
        if 'Legendary' in q.tl or len(q.colors) > 2 or norm(r['name']) not in fn: continue
        rows.append(dict(name=r['name'], actual=r.actual_gih, colors=q.colors, mv=q.mv, pair=pair_for(r['name'], q.colors)))
    d = pd.DataFrame(rows).sort_values('actual'); sel = pd.concat([d.head(6).assign(grp='bottom'), d.tail(6).assign(grp='top')])
    sel.to_csv(HERE + '/selected.csv', index=False); print(sel.to_string(index=False)); print('eligible', len(d))
def build():
    p = gen.pool(SET); sel = pd.read_csv(HERE + '/selected.csv'); jobs = []
    rng = random.Random(20261018)
    opps = []
    for i, pr in enumerate(['WU', 'BR', 'RG', 'UB']):          # fixed opponents, different pairs
        gen.write(f'{DECKS}/j1_opp{i}.dck', SET, gen.deck(p, pr, rng), pr); opps.append(f'j1_opp{i}.dck')
    base = {}
    for pr in sorted(sel.pair.unique()):
        sp = gen.deck(p, pr, random.Random(hash_s(pr))); gen.write(f'{DECKS}/j1_B_{pr}.dck', SET, sp, pr); base[pr] = sp
    for _, r in sel.iterrows():
        sp = list(base[r.pair]); idx = [i for i, n in enumerate(sp) if n != r['name']]
        rr = random.Random(hash_s(r['name'])); rr.shuffle(idx)
        for i in idx[:max(0, 4 - base[r.pair].count(r['name']))]: sp[i] = r['name']
        gen.write(f'{DECKS}/j1_V_{norm(r["name"])}.dck', SET, sp, r.pair)
        for k, o in enumerate(opps): jobs.append((f'V_{norm(r["name"])}_{k}', f'j1_V_{norm(r["name"])}.dck', o, 1000 + k))
    for pr in base:
        for k, o in enumerate(opps): jobs.append((f'B_{pr}_{k}', f'j1_B_{pr}.dck', o, 1000 + k))
    return jobs
def hash_s(s): return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)
def job(fd, j):
    jid, a, b, seed = j; out = f'{RES}/{jid}.json'
    if os.path.exists(out): return jid
    cmd = ['java', '-Xmx1g', '-jar', fd + '/forge-gui-desktop/target/forge-gui-desktop-2.0.16-SNAPSHOT-jar-with-dependencies.jar',
           'sim', '-d', a, b, '-n', str(NG), '-s', str(seed), '-q', '-c', '120']
    t = subprocess.run(cmd, cwd=fd + '/forge-gui', capture_output=True, text=True, timeout=3600).stdout
    m = re.findall(r'Match Result: Ai\(1\)-[^:]+: (\d+) Ai\(2\)-[^:]+: (\d+)', t)
    if not m: open(out + '.err', 'w').write(t[-2000:]); raise RuntimeError(jid)
    w1, w2 = map(int, m[-1]); json.dump(dict(w=w1, l=w2), open(out, 'w')); return jid
def run(fd):
    jobs = build(); todo = [j for j in jobs if not os.path.exists(f'{RES}/{j[0]}.json')]; print('jobs', len(jobs), 'todo', len(todo), flush=True)
    with cf.ThreadPoolExecutor(2) as ex:
        for f in cf.as_completed([ex.submit(job, fd, j) for j in todo]):
            try: print('done', f.result(), flush=True)
            except Exception as e: print('FAIL', e, flush=True)
def report():
    from scipy.stats import spearmanr
    sel = pd.read_csv(HERE + '/selected.csv'); rows = []
    def wr(prefix):
        w = l = 0
        for f in os.listdir(RES):
            if f.startswith(prefix) and f.endswith('.json'): d = json.load(open(f'{RES}/{f}')); w += d['w']; l += d['l']
        return w, w + l
    for _, r in sel.iterrows():
        wv, nv = wr(f'V_{norm(r["name"])}_'); wb, nb = wr(f'B_{r.pair}_')
        if not nv or not nb: continue
        pv, pb = wv / nv, wb / nb; se = np.sqrt(pv * (1 - pv) / nv + pb * (1 - pb) / nb)
        rows.append(dict(name=r['name'], grp=r.grp, actual=r.actual, delta=(pv - pb) * 100, se=se * 100, nV=nv, nB=nb))
    d = pd.DataFrame(rows); print(d.round(2).to_string(index=False))
    if len(d) == 12:
        t, b = d[d.grp == 'top'], d[d.grp == 'bottom']; diff = t.delta.mean() - b.delta.mean()
        se = np.sqrt((t.se ** 2).sum() / 36 + (b.se ** 2).sum() / 36); rho = spearmanr(d.delta, d.actual)[0]
        ok = diff >= 1.5 * se and rho >= 0.4
        print(f'top-bottom {diff:+.2f}pp se {se:.2f} ratio {diff / se:.2f}  Spearman {rho:.3f}  Rule J1: {"PASS" if ok else "FAIL"}')
        json.dump(dict(diff=diff, se=se, rho=rho, pass_=bool(ok)), open(HERE + '/result.json', 'w'))
    d.to_csv(HERE + '/deltas.csv', index=False)
if __name__ == '__main__':
    a = sys.argv[1]
    if a == 'select': select(sys.argv[2])
    elif a == 'run': run(sys.argv[2])
    else: report()
