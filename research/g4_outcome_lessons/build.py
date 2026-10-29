"""G4 inputs. python3 build.py (deterministic)"""
import runpy, sys, re, numpy as np, pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent; G = H.parent/'g3_expert_grade'
sys.argv = ['x']; ns = runpy.run_path(str(G/'build.py')); o, fc, LS = ns['o'], ns['fc'], ns['LESSON_SETS']
# lesson material: biggest B10 misses in the 11 lesson sets (within-set), 300 under + 150 over
L = o[o.set.isin(LS)].copy()
L['y'] = (L.actual_gih - L.groupby('set').actual_gih.transform('mean'))*100
L['p'] = (L.pred - L.groupby('set').pred.transform('mean'))*100; L['res'] = L.y - L.p
L['rk'] = L.groupby('set').p.rank(ascending=False).astype(int); L['n'] = L.groupby('set').p.transform('size')
pick = pd.concat([L.nlargest(300, 'res'), L.nsmallest(150, 'res')]).sample(frac=1, random_state=4)
with open(H/'lesson_material.txt', 'w') as f:
    f.write('Each card: [set] name, then text. model = B10 prediction (pp vs set mean, rank in set); actual = real GIH WR (pp vs set mean); miss = actual - model; expert = pre-release human grade 0-5 (if any).\n\n')
    for r in pick.itertuples():
        ex = f'{r.grade:.1f}/5' if r.grade == r.grade else 'n/a'
        f.write(fc(r.key, r.rarity_ord, f'[{r.set}] {r.name}') + f"\nmodel {r.p:+.1f} (rank {r.rk}/{r.n}) | actual {r.y:+.1f} | miss {r.res:+.1f} | expert {ex}\n\n")
# per-set summary of B10 bias in lesson sets (helps set-level lessons)
(H/'keys').mkdir(exist_ok=True)
for T in ['FRA', 'TMT', 'ECL']:
    k = pd.read_csv(G/T/'targets_key.csv'); out = H/T; out.mkdir(exist_ok=True)
    k['p'] = (k.pred - k.pred.mean())*100; k['rk'] = k.p.rank(ascending=False).astype(int)
    blocks = [b.strip() for b in re.split(r'\n\s*\n(?=#T\d+ )', (G/T/'targets.txt').read_text().strip())]; assert len(blocks) == len(k)
    txt = []
    for b, r in zip(blocks, k.itertuples()):
        assert b.startswith(f'#{r.tid} '), (b[:10], r.tid); txt.append(b + f'\nmodel {r.p:+.1f} pp (rank {r.rk}/{len(k)})')
    (out/'targets.txt').write_text('\n\n'.join(txt) + '\n'); k.to_csv(H/'keys'/f'{T}.csv', index=False)
    print(T, len(k))
print('lesson rows', len(pick))
