#!/usr/bin/env python3
"""Step 1 of PLAN.md: can Sonnet replace Opus as the labeller for B10? (FRA 100-card check, no outcomes used)

  python3 sonnet_check.py sample --fra <pages>/data/target.json.gz   # fra100/sample.csv
  python3 sonnet_check.py inputs                                     # fra100/input/<pass>.txt (blinded, production card view)
  python3 sonnet_check.py check                                      # validate fra100/raw/<pass>.txt
  python3 sonnet_check.py score  --fra <pages>/data/target.json.gz   # fra100/result.json (Rule S1)
"""
import argparse, gzip, json, random, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
R = HERE.parents[0]
OUT = HERE / 'fra100'
SEED = 20261021
QUOTA = {'common': 25, 'uncommon': 30, 'rare': 25, 'mythic': 20}
PASSES = ['c3', 'c4', 'c5', 'c9p1', 'c9p2', 'c9p3']
QUEUE = {'c3': R / 'gih_llm_extract/cards.csv.gz', 'c4': R / 'c4_fine_effects/cards.csv.gz',
         'c5': R / 'c5_atomic_effects/cards.csv.gz', 'c9p1': R / 'c9_power_questions/cards.csv.gz',
         'c9p2': R / 'c9_power_questions/cards.csv.gz', 'c9p3': R / 'c9_power_questions/cards.csv.gz'}
RUBRIC = {'c3': R / 'gih_llm_extract/RUBRIC.md', 'c4': R / 'c4_fine_effects/RUBRIC.md', 'c5': R / 'c5_atomic_effects/RUBRIC.md',
          'c9p1': R / 'c9_power_questions/RUBRIC.md', 'c9p2': R / 'c9_power_questions/RUBRIC.md', 'c9p3': R / 'c9_power_questions/RUBRIC.md'}


def key_rows(path):
    q = pd.read_csv(path, keep_default_na=False)
    rows = {}
    for r in q.itertuples():
        for k in str(r.keys).split(';'):
            rows[k] = r
    return rows


def card_view(r, i):
    head = f"#{i} | MV {r.mv} {r.colors or 'C'} | {r.type_line}" + (f" | {r.pt}" if r.pt else "")
    return head + "\n" + r.btext.replace("\n", " / ")


def cmd_sample(a):
    fra = json.loads(gzip.open(a.fra, 'rt', encoding='utf-8').read())['cards']
    autos = {k for p in set(QUEUE.values()) for k, r in key_rows(p).items() if r.auto == 1}
    rng = np.random.default_rng(SEED)
    pick = []
    for rar, n in QUOTA.items():
        pool = [c for c in fra if c['rarity'] == rar and f"FRA|{c['id']}" not in autos]
        idx = rng.choice(len(pool), n, replace=False)
        pick += [pool[i] for i in sorted(idx)]
    order = rng.permutation(len(pick))
    s = pd.DataFrame([{'key': f"FRA|{pick[j]['id']}", 'name': pick[j]['name'], 'rarity': pick[j]['rarity']} for j in order])
    s.insert(0, 'sid', np.arange(1, len(s) + 1))
    OUT.mkdir(exist_ok=True)
    s.to_csv(OUT / 'sample.csv', index=False)
    print(s['rarity'].value_counts().to_dict())


def cmd_inputs(_a):
    s = pd.read_csv(OUT / 'sample.csv')
    (OUT / 'input').mkdir(exist_ok=True)
    (OUT / 'raw').mkdir(exist_ok=True)
    for p in PASSES:
        rows = key_rows(QUEUE[p])
        cards = [card_view(rows[k], i) for k, i in zip(s['key'], s['sid'])]
        if p == 'c9p2':
            cards = cards[::-1]
        elif p == 'c9p3':
            random.Random(SEED).shuffle(cards)
        (OUT / 'input' / f'{p}.txt').write_text('\n\n'.join(cards) + f'\n-- {len(cards)} cards\n')
    print('inputs written', len(s))


# ---- parsing (same formats and ranges as the production check_raw files)
C3L, C3MAX, C3DEP = re.compile(r"^(\d+) ([0-9]{10}) (\S)$"), [3, 2, 3, 3, 2, 1, 3, 2, 1, 1], set("-TGAESKCLXHMO")
C4L, C4MAX, C4ROLE = re.compile(r"^(\d+) ([0-9]{14}) ([A-Z])$"), [4, 4, 3, 4, 3, 3, 3, 2, 2, 2, 5, 2, 3, 2], set("ADVFRTSNO")
C9L, C9MAX = re.compile(r'^(\d+)((?: \d+){7})\s*$'), [4, 4, 4, 4, 3, 4, 10]


def parse(p, line):
    line = line.strip()
    if p == 'c3':
        m = C3L.match(line)
        if not m: return None
        v = [int(c) for c in m.group(2)]
        if any(x > y for x, y in zip(v, C3MAX)) or m.group(3) not in C3DEP: return None
        return int(m.group(1)), v + [m.group(3)]
    if p == 'c4':
        m = C4L.match(line)
        if not m: return None
        v = [int(c) for c in m.group(2)]
        if any(x > y for x, y in zip(v, C4MAX)) or m.group(3) not in C4ROLE: return None
        return int(m.group(1)), (v, m.group(3))
    if p == 'c5':
        sys.path.insert(0, str(R / 'c5_atomic_effects'))
        import check_raw as c5cr
        r, err = c5cr.parse(line)
        return None if err else (r[0], (r[1], r[2]))
    m = C9L.match(line)
    if not m: return None
    v = [int(x) for x in m.group(2).split()]
    if any(x > y for x, y in zip(v, C9MAX)): return None
    return int(m.group(1)), v


def load(p):
    out, bad = {}, []
    f = OUT / 'raw' / f'{p}.txt'
    if not f.exists():
        return out, [f'{p}: missing file']
    for n, line in enumerate(f.read_text().splitlines(), 1):
        if not line.strip(): continue
        r = parse(p, line)
        if r is None or r[0] in out:
            bad.append(f'{p}:{n} {line!r}'); continue
        out[r[0]] = r[1]
    return out, bad


def cmd_check(_a):
    s = pd.read_csv(OUT / 'sample.csv')
    ok = True
    for p in PASSES:
        out, bad = load(p)
        miss = sorted(set(s['sid']) - set(out)); extra = sorted(set(out) - set(s['sid']))
        print(p, 'labelled', len(out), 'missing', miss[:10], 'extra', extra[:10], 'errors', bad[:5])
        ok &= not (miss or extra or bad)
    if not ok: raise SystemExit(1)


# ---- scoring
def sonnet_tables(s):
    sys.path.insert(0, str(R / 'gih_llm_extract'))
    sys.path.insert(0, str(R / 'c9_power_questions'))
    import c9
    c5 = c9.c5
    import c3_research as c3
    raw = {p: load(p)[0] for p in PASSES}
    c3rows = key_rows(QUEUE['c3'])
    x = pd.DataFrame([raw['c3'][i] for i in s['sid']], columns=c3.FIELDS + ['dep'])
    t3 = c3.c3_columns(x, pd.Series([c3rows[k].mv for k in s['key']]))
    t3.index = s['key']
    t4 = pd.DataFrame([{**{n: v for n, v in zip(c5.C4_NUM, raw['c4'][i][0])},
                         **{f'c4_role_{r}': float(raw['c4'][i][1] == r) for r in 'ADVFRTSNO'}} for i in s['sid']], index=s['key'])
    rows5 = []
    for i in s['sid']:
        sc, tg = raw['c5'][i]
        d = {f'c5_{t}': tg.get(t, 0) for t in c5.cr.TAGS}
        d.update(dict(zip(c5.SCALE, sc)))
        d['c5_ntags'] = len(tg); d['c5_nlvl2'] = sum(1 for v in tg.values() if v == 2)
        d['c5_ngroups'] = sum(any(t in tg for t in g.split()) for g in c5.GROUPS.values())
        rows5.append(d)
    t5 = pd.DataFrame(rows5, index=s['key'])
    rows9 = []
    for i in s['sid']:
        v = np.array([raw[p][i] for p in ('c9p1', 'c9p2', 'c9p3')], float)
        m, sd = v.mean(0), v.std(0)
        d = dict(zip(c9.MEAN, m)); d.update(dict(zip(c9.SD, sd)))
        d['c9_impuna'] = m[0] + m[1]; d['c9_valfloor'] = m[2] + m[3]; d['c9_bomb'] = m[6] - 1.25 * m[5]
        rows9.append(d)
    t9 = pd.DataFrame(rows9, index=s['key'])
    return t3, t4, t5, t9, raw


def label_agreement(s, raw):
    """Sonnet vs Opus labels on the 100 cards, per field."""
    sys.path.insert(0, str(R / 'c9_power_questions'))
    import c9
    rep = {}
    o9 = pd.read_csv(R / 'c9_power_questions/c9_features.csv.gz').set_index('key').loc[s['key']]
    for j, f in enumerate(c9.F):
        sm = np.array([np.mean([raw[p][i][j] for p in ('c9p1', 'c9p2', 'c9p3')]) for i in s['sid']])
        om = o9[f'c9_m_{f}'].to_numpy()
        rep[f'C9_{f}'] = {'spearman': round(float(spearmanr(sm, om)[0]), 3), 'mean_sonnet': round(float(sm.mean()), 3),
                          'mean_opus': round(float(om.mean()), 3)}
    o3 = pd.read_csv(R / 'gih_llm_extract/c3_features.csv.gz', keep_default_na=False).set_index('key').loc[s['key']]
    for j, f in enumerate(['removal', 'sweeper', 'bodies', 'cards', 'repeat', 'modal', 'dependency', 'drawback', 'trick', 'sink']):
        sv = np.array([raw['c3'][i][j] for i in s['sid']]); ov = o3[f].astype(int).to_numpy()
        rep[f'C3_{f}'] = {'exact': round(float((sv == ov).mean()), 3), 'mean_sonnet': round(float(sv.mean()), 3), 'mean_opus': round(float(ov.mean()), 3)}
    o4 = pd.read_csv(R / 'c4_fine_effects/c4_features.csv.gz').set_index('key').loc[s['key']]
    for j, f in enumerate(['DMG', 'TGT', 'SPD', 'SWG', 'EVA', 'TURN', 'DEAD', 'SCALE', 'TEMPO', 'VULN', 'STACK', 'SYNO', 'DRAIN', 'MANA']):
        sv = np.array([raw['c4'][i][0][j] for i in s['sid']]); ov = o4[f'c4_{f}'].to_numpy()
        rep[f'C4_{f}'] = {'exact': round(float((sv == ov).mean()), 3), 'mean_sonnet': round(float(sv.mean()), 3), 'mean_opus': round(float(ov.mean()), 3)}
    o5 = pd.read_csv(R / 'c5_atomic_effects/c5_features.csv.gz').set_index('key').loc[s['key']]
    for j, f in enumerate(['RATE', 'CLK', 'BLK']):
        sv = np.array([raw['c5'][i][0][j] for i in s['sid']]); ov = o5[f'c5_{f}'].to_numpy()
        rep[f'C5_{f}'] = {'exact': round(float((sv == ov).mean()), 3), 'mean_sonnet': round(float(sv.mean()), 3), 'mean_opus': round(float(ov.mean()), 3)}
    sn = np.array([len(raw['c5'][i][1]) for i in s['sid']]); on = o5['c5_ntags'].to_numpy()
    rep['C5_ntags'] = {'mean_sonnet': round(float(sn.mean()), 3), 'mean_opus': round(float(on.mean()), 3)}
    return rep


def cmd_score(a):
    sys.path.insert(0, str(R / 'c9_power_questions'))
    import c9
    c5, e = c9.c5, c9.e
    s = pd.read_csv(OUT / 'sample.csv')
    pool, base, cols = c9.load_pool()
    fra, f = e.fra_frame(a.fra, base, cols, pool)
    keys = [f"FRA|{c['id']}" for c in fra]
    groups = {'c4': c5.C4_NUM + c5.C4_ROLE, 'c5': c5.TAGC + c5.SCALE + c5.CNT, 'c9': c9.MEAN + c9.SD + c9.SUM}
    for src, names in ((c5.C4DIR / 'c4_features.csv.gz', groups['c4']), (c5.HERE / 'c5_features.csv.gz', groups['c5']),
                       (c9.HERE / 'c9_features.csv.gz', groups['c9'])):
        t = pd.read_csv(src).set_index('key')
        for c in names:
            f[c] = t.loc[keys, c].to_numpy(dtype=float)
    groups['c3'] = list(cols)
    nums = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    t3, t4, t5, t9, raw = sonnet_tables(s)
    son = {'c3': t3, 'c4': t4, 'c5': t5, 'c9': t9}
    pos = pd.Series(range(len(keys)), index=keys).loc[s['key']].to_numpy()
    frozen = pd.read_csv(R / 'c9_power_questions/fra_frozen_predictions.csv').set_index('id')['pred_B10']

    def run(swap):
        g = f.copy()
        for k in swap:
            for c in groups[k]:
                g.loc[pos, c] = son[k].loc[s['key'], c].to_numpy(dtype=float)
        return e.predict(pool, g, nums)[3]

    preds = {'O': run([])}
    repro = float(np.abs(preds['O'] - frozen.loc[[c['id'] for c in fra]].to_numpy()).max())
    preds['S'] = run(['c3', 'c4', 'c5', 'c9'])
    for k in ('c3', 'c4', 'c5', 'c9'):
        preds[f'only_{k}'] = run([k])
    O = preds['O'][pos] * 100
    res = {'reproduce_frozen_maxdiff': repro, 'n': len(s)}
    for name, p in preds.items():
        if name == 'O': continue
        d = p[pos] * 100 - O
        res[name] = {'mean_abs_pp': round(float(np.abs(d).mean()), 3), 'mean_pp': round(float(d.mean()), 3),
                     'pearson': round(float(np.corrcoef(p[pos] * 100, O)[0, 1]), 4), 'max_abs_pp': round(float(np.abs(d).max()), 2)}
    S = preds['S'][pos] * 100
    r = res['S']
    res['rule_S1'] = {'mean_abs<=0.40': r['mean_abs_pp'] <= .40, '|mean|<=0.20': abs(r['mean_pp']) <= .20, 'pearson>=0.95': r['pearson'] >= .95}
    res['rule_S1']['pass'] = all(res['rule_S1'].values())
    by = {}
    for rar in QUOTA:
        m = (s['rarity'] == rar).to_numpy()
        by[rar] = {'mean_pp': round(float((S - O)[m].mean()), 3), 'mean_abs_pp': round(float(np.abs(S - O)[m].mean()), 3)}
    res['S_by_rarity'] = by
    top = np.argsort(-O)[:10]
    rs = pd.Series(S).rank(ascending=False).to_numpy()
    res['top10_by_O'] = [{'name': s['name'][i], 'rarity': s['rarity'][i], 'O': round(float(O[i]), 2), 'S': round(float(S[i]), 2),
                          'rank_O': int(k + 1), 'rank_S': int(rs[i])} for k, i in enumerate(top)]
    res['labels'] = label_agreement(s, raw)
    pd.DataFrame({'key': s['key'], 'name': s['name'], 'rarity': s['rarity'], 'pred_O': O, 'pred_S': S}).to_csv(OUT / 'pred_compare.csv', index=False)
    json.dump(res, open(OUT / 'result.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k not in ('labels', 'top10_by_O')}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for n, fn in (('sample', cmd_sample), ('inputs', cmd_inputs), ('check', cmd_check), ('score', cmd_score)):
        p = sub.add_parser(n); p.set_defaults(f=fn)
        if n in ('sample', 'score'):
            p.add_argument('--fra', type=Path, required=True)
    a = ap.parse_args(); a.f(a)


if __name__ == '__main__':
    main()
