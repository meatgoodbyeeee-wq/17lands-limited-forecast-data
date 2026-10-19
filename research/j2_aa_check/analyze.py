import json, math, os, sys
def load(d):
    g = []
    for o in range(4):
        for r in json.load(open(f'games/{d}_{o}.json')): r['opp'] = o; g.append(r)
    return g
B = {k: load(f'B{k}c') for k in (1, 2, 3)}; Ball = [r for k in B for r in B[k]]
def ref(Bgames, t): 
    s = [r for r in Bgames if r['turns'] >= t]; return (sum(r['win1'] for r in s) / len(s)) if s else float('nan')
def report(name, games, Bgames):
    n = len(games); drew = [r for r in games if r['ndrew'] > 0]; cast = [r for r in games if r['ncast'] > 0]
    all_wr = sum(r['win1'] for r in games) / n
    out = dict(name=name, n=n, p_drew=len(drew) / n, all_wr=all_wr)
    if drew:
        w = sum(r['win1'] for r in drew) / len(drew); rf = sum(ref(Bgames, r['first_draw']) for r in drew) / len(drew)
        se = math.sqrt(w * (1 - w) / len(drew)); out.update(n_drew=len(drew), drew_wr=w, ref=rf, delta_drew=(w - rf) * 100, se=se * 100,
            nodrew_wr=sum(r['win1'] for r in games if r['ndrew'] == 0) / max(1, n - len(drew)))
    if cast:
        w = sum(r['win1'] for r in cast) / len(cast); rf = sum(ref(Bgames, r['first_cast']) for r in cast) / len(cast)
        out.update(n_cast=len(cast), cast_wr=w, ref_cast=rf, delta_cast=(w - rf) * 100,
                   drew_not_cast=sum(1 for r in drew if r['ncast'] == 0) / max(1, len(drew)))
    return out
rows = [report('V (AA x4, all patterns)', load('V'), Ball)]
Vg = load('V')
for lab, pre in (('V2 (AA x2)', 'V2'), ('V1 (AA x1)', 'V1')):
    gs = []; ok = True
    for k in (1, 2, 3):
        if not os.path.exists(f'games/{pre}_{k}_0.json'): ok = False; break
        g = load(f'{pre}_{k}'); gs.append((g, B[k]))
    if ok:
        allg = [r for g, _ in gs for r in g]
        # reference per pattern B
        n = len(allg); drew = [(r, Bk) for g, Bk in gs for r in g if r['ndrew'] > 0]
        w = sum(r['win1'] for r, _ in drew) / len(drew); rf = sum(ref(Bk, r['first_draw']) for r, Bk in drew) / len(drew)
        cast = [(r, Bk) for g, Bk in gs for r in g if r['ncast'] > 0]; wc = sum(r['win1'] for r, _ in cast) / len(cast); rc = sum(ref(Bk, r['first_cast']) for r, Bk in cast) / len(cast)
        rows.append(dict(name=lab, n=n, p_drew=len(drew) / n, all_wr=sum(r['win1'] for r in allg) / n, n_drew=len(drew), drew_wr=w, ref=rf, delta_drew=(w - rf) * 100,
                         se=math.sqrt(w * (1 - w) / len(drew)) * 100, n_cast=len(cast), cast_wr=wc, ref_cast=rc, delta_cast=(wc - rc) * 100))
print('B (AA x0) overall win rate: %.3f over %d games' % (sum(r['win1'] for r in Ball) / len(Ball), len(Ball)))
for r in rows:
    print(r['name'], '| games', r['n'], '| all-games WR %.3f' % r['all_wr'], '| P(AA drawn) %.2f' % r['p_drew'])
    print('   drawn games: n=%d  WR %.3f  vs matched B %.3f  -> delta_drew %+.1f pp (se ~%.1f)' % (r['n_drew'], r['drew_wr'], r['ref'], r['delta_drew'], r['se']))
    print('   cast  games: n=%d  WR %.3f  vs matched B %.3f  -> delta_cast %+.1f pp' % (r['n_cast'], r['cast_wr'], r['ref_cast'], r['delta_cast']))
    if 'nodrew_wr' in r: print('   not-drawn games WR %.3f ; drawn-but-not-cast share %.2f' % (r['nodrew_wr'], r['drew_not_cast']))
json.dump(rows, open('result_j2d.json', 'w'), indent=1, default=float)
