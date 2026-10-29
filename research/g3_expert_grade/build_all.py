"""G3 inputs for ALL 28 training sets (Plan A). python3 build_all.py  (deterministic)
Per set S: all/S/{examples.txt,targets.txt} (judge folder, no outcomes), keys_all/S.csv (answer key, NOT in judge folder).
Examples = expert-graded cards from the 13 graded past sets EXCLUDING S itself."""
import runpy, sys, pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent
sys.argv = ['x']
ns = runpy.run_path(str(H/'build.py'))          # reuses o, fc, PAST, c9 (also regenerates pilot files deterministically)
o, fc, PAST, c9 = ns['o'], ns['fc'], ns['PAST'], ns['c9']
(H/'all').mkdir(exist_ok=True); (H/'keys_all').mkdir(exist_ok=True)
sets = sorted(o.set.unique()); print(len(sets), 'sets')
for T in sets:
    out = H/'all'/T; out.mkdir(exist_ok=True)
    ex = o[o.set.isin([s for s in PAST if s != T]) & o.grade.notna()]
    ex = ex.groupby('set', group_keys=False).apply(lambda g: g.sample(min(len(g), 66), random_state=1)).sample(frac=1, random_state=2)
    (out/'examples.txt').write_text('\n'.join(fc(r.key, r.rarity_ord, f'#E{i+1}') + f"\n=> expert {r.grade:.1f}/5\n" for i, r in enumerate(ex.itertuples())))
    tg = o[o.set == T].sample(frac=1, random_state=3).reset_index(drop=True)
    (out/'targets.txt').write_text('\n\n'.join(fc(r.key, r.rarity_ord, f'#T{i+1}') for i, r in enumerate(tg.itertuples())) + '\n')
    pd.DataFrame({'tid': [f'T{i+1}' for i in range(len(tg))], 'key': tg.key, 'name': tg.name, 'rarity_ord': tg.rarity_ord,
                  'actual_gih': tg.actual_gih, 'pred': tg.pred, 'c9_grade': tg.key.map(c9), 'expert': tg.grade}).to_csv(H/'keys_all'/f'{T}.csv', index=False)
    print(T, 'examples', len(ex), 'targets', len(tg))
