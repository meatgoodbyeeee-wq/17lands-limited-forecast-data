#!/usr/bin/env python3
"""G1 v2 route check (PLAN_v2.md 12.2): re-judge the first 60 cards of old C9 input/p1/b00.txt with the OLD rubric
through the same `claude -p` call as v2, and compare with the old C9 p1 answers.

  python3 route_check.py run      # one call -> route_check/raw.txt (skips if already valid)
  python3 route_check.py score    # route_check/result.json; exit 1 if the stop condition is met

Stop condition (fixed before the call): GRADE Spearman < 0.75, or |mean GRADE difference| > 0.5.
"""
import json, re, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
C9 = HERE.parent / 'c9_power_questions'
OUT = HERE / 'route_check'
N = 60
F = ['IMP', 'UNA', 'VAL', 'FLOOR', 'FLEX', 'PLAY', 'GRADE']
sys.path.insert(0, str(HERE))
import run_v2 as rv  # noqa: E402


def build():
    txt = (C9 / 'input' / 'p1' / 'b00.txt').read_text()
    cards = [c.strip() for c in re.split(r'\n(?=#\d+ \|)', txt.split('\n-- ')[0]) if c.strip().startswith('#')][:N]
    OUT.mkdir(exist_ok=True)
    (OUT / 'input').mkdir(exist_ok=True)
    (OUT / 'input' / 'route.txt').write_text('\n\n'.join(cards) + f'\n-- route check: {len(cards)} cards\n')


def run():
    build()
    r = rv.judge_batch('route', 'route', system_file=C9 / 'RUBRIC.md', in_dir=OUT / 'input', out_dir=OUT / 'raw', log_dir=OUT / 'log')
    print(r)
    return 0 if r in ('ok', 'skip') else 1


def load(f):
    d = {}
    for line in f.read_text().splitlines():
        m = rv.LINE.match(line.strip())
        if m:
            d[int(m.group(1))] = [int(x) for x in m.group(2).split()]
    return d


def score():
    new = load(OUT / 'raw' / 'route.txt')
    old = {}
    for f in sorted((C9 / 'raw' / 'p1').glob('b*.txt')):
        old.update(load(f))
    ids = sorted(new)
    a, b = np.array([old[i] for i in ids], float), np.array([new[i] for i in ids], float)
    res = {'n': len(ids), 'fields': {}}
    for k, f in enumerate(F):
        res['fields'][f] = {'spearman': round(float(spearmanr(a[:, k], b[:, k]).correlation), 3),
                            'mean_old': round(float(a[:, k].mean()), 3), 'mean_new': round(float(b[:, k].mean()), 3),
                            'mean_diff': round(float((b[:, k] - a[:, k]).mean()), 3), 'exact': round(float((a[:, k] == b[:, k]).mean()), 3)}
    g = res['fields']['GRADE']
    res['stop'] = bool(g['spearman'] < 0.75 or abs(g['mean_diff']) > 0.5)
    res['reference'] = 'old C9 inter-pass GRADE Spearman 0.825-0.898 (agreement.json)'
    (OUT / 'result.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 1 if res['stop'] else 0


if __name__ == '__main__':
    sys.exit({'run': run, 'score': score}[sys.argv[1]]())
