"""F1 build: reference ladders + judge inputs. python3 build.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
H = Path(__file__).resolve().parent; R = H.parent; A2 = R / 'a2_forced_deck_ev'
sys.path.insert(0, str(A2)); import a2
CARDS = a2.CARDS.set_index(['set', 'id']); entry = a2.entry
act = pd.read_csv(R / 'c9_power_questions/oof_B10.csv.gz'); act['c'] = (act.actual_gih - act.groupby('set').actual_gih.transform('mean')) * 100
act['key'] = act.set + '|' + act.name
sel = pd.read_csv(A2 / 'selected.csv'); sel = sel.merge(act[['key', 'c']], on='key', how='left').dropna(subset=['c'])
Q = [3, 15, 30, 45, 60, 75, 88, 96, 100]
sub = pd.read_csv(R / 'h1_judge_reliability/subset.csv')


def ladder(s):
    p = sel[sel.set != s].sort_values(['c', 'key']).reset_index(drop=True)
    idx = sorted({min(len(p) - 1, int(round(q / 100 * (len(p) - 1)))) for q in Q})
    return p.iloc[idx]


def block(s):
    out = []
    for n, r in enumerate(ladder(s).itertuples(), 1):
        c = CARDS.loc[(r.set, r.id)]; rr = type('R', (), {**c.to_dict(), 'id': f'REF{n}'})
        out.append(entry(rr).replace('#REF', 'REF', 1) + f"\nMEASURED: {r.c:+.1f} pp vs average card of its set")
    return '\n\n'.join(out)


def main():
    cache = {}
    for r in sub.itertuples():
        if r.set not in cache: cache[r.set] = block(r.set)
        txt = '# REFERENCE CARDS (from other sets)\n\n' + cache[r.set] + '\n\n# DECK AND TARGET\n\n' + (A2 / 'judge_in' / f'{r.name}.txt').read_text()
        (H / 'in' / f'{r.name}.txt').write_text(txt)
    names = list(sub.name)
    for i in range(0, len(names), 10): (H / 'batches' / f'b{i // 10:02d}.txt').write_text('\n'.join(names[i:i + 10]) + '\n')
    print(len(names), 'inputs;', len(cache), 'ladders')


if __name__ == '__main__':
    main()
