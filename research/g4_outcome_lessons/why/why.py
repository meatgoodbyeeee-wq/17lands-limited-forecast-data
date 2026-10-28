"""Why do G4 lessons not transfer? For each main lesson, a text/stat rule, and B10's mean residual (actual - pred, within set, pp)
for matching cards: in the 11 lesson sets (in-sample), the 17 other sets (out-of-sample), and per set (sign consistency)."""
import runpy, sys, re, numpy as np, pandas as pd
from pathlib import Path
G = Path(__file__).resolve().parents[2]/'g3_expert_grade'
sys.argv = ['x']; ns = runpy.run_path(str(G/'build.py')); o, k2, LS = ns['o'].copy(), ns['k2'], ns['LESSON_SETS']
o['txt'] = [str(k2[k].btext).lower() if k in k2 else '' for k in o.key]
o['typ'] = [str(k2[k].type_line).lower() if k in k2 else '' for k in o.key]
o['mv'] = [float(k2[k].mv) if k in k2 and str(k2[k].mv) not in ('', 'nan') else np.nan for k in o.key]
o['y'] = (o.actual_gih - o.groupby('set').actual_gih.transform('mean'))*100
o['p'] = (o.pred - o.groupby('set').pred.transform('mean'))*100; o['res'] = o.y - o.p
o['pq'] = o.groupby('set').p.rank(pct=True)
cre = o.typ.str.contains('creature')
R = {
 'L1 top 5% predicted': o.pq >= .95,
 'L3 bottom 5% predicted': o.pq <= .05,
 'L4 plain card draw (draw two/three, non-creature)': o.txt.str.contains(r'draw (two|three) cards') & ~cre,
 'L5 discard (opponent discards)': o.txt.str.contains(r'(opponent|player) (reveals|discards)'),
 'L6 counterspell': o.txt.str.contains(r'counter target'),
 'L2 MV>=6 creature with attack trigger': cre & (o.mv >= 6) & o.txt.str.contains(r'whenever ~ attacks'),
 'removal: destroy/exile target creature': o.txt.str.contains(r'(destroy|exile) target (creature|nonland permanent)'),
 'all cards (control)': o.set == o.set,
}
rows = []
for n, m in R.items():
    g = o[m]; a, b = g[g.set.isin(LS)], g[~g.set.isin(LS)]
    ps = g.groupby('set').res.mean(); cnt = g.groupby('set').size(); ps = ps[cnt >= 3]
    sign = np.sign(a.res.mean())
    rows.append({'lesson': n, 'n': len(g), 'res_lesson11': a.res.mean(), 'res_other17': b.res.mean(),
                 'sets_same_sign_as_lesson': f'{int((np.sign(ps) == sign).sum())}/{len(ps)}', 'between_set_sd': ps.std()})
t = pd.DataFrame(rows); print(t.round(2).to_string())
# how extreme is the lesson sample? regression to the mean check: residual noise floor
print('residual sd within set %.2f; share of |res|>4: %.2f' % (o.res.std(), (o.res.abs() > 4).mean()))
# top-tail stretch test (LOSO): add constant k to cards with predicted percentile >= q, k = mean residual of those cards in other sets
for q in (.90, .95):
    m = o.pq >= q; adj = np.zeros(len(o))
    for s in o.set.unique():
        te = (o.set == s).to_numpy(); adj[te & m.to_numpy()] = o[~te & m].res.mean()
    for grp, sel in [('other17', ~o.set.isin(LS)), ('all28', o.set == o.set)]:
        g = o[sel]; a = adj[sel.to_numpy()]
        print(f'top-stretch q={q} {grp}: MAE {g.res.abs().mean():.3f} -> {(g.res - a).abs().mean():.3f}')
