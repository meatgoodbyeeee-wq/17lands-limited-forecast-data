#!/usr/bin/env python3
"""Build C10 targets, anchor ladders and blinded input batches (before any judging). See PLAN.md.

  python3 build.py
"""
import gzip, json, random, re
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parent
FRA = Path('/home/claude/limited-forecast-pages/data/target.json.gz')
BATCH = 65
SD_MIN = 0.6
QS = [5, 20, 35, 50, 65, 80, 95]
MAXLEN = 300


def blocks():
    out = {}
    for f in sorted((R / 'c5_atomic_effects/input').glob('b*.txt')):
        txt = f.read_text().split('\n-- batch')[0]
        for c in re.split(r'\n(?=#\d+ \|)', txt):
            c = c.strip()
            if c.startswith('#'):
                out[int(re.match(r'#(\d+)', c).group(1))] = c
    return out


def targets():
    u = pd.read_csv(R / 'c9_power_questions/cards.csv.gz', keep_default_na=False)
    o = pd.read_csv(R / 'c5_atomic_effects/oof_B5.csv.gz')[['set', 'name', 'rarity_ord']]
    o['key'] = o['set'] + '|' + o['name']
    rar = o.set_index('key')['rarity_ord'].to_dict()
    fra = {f"FRA|{c['id']}": {'common': 0, 'uncommon': 1, 'rare': 2, 'mythic': 3}.get(c['rarity'], -1) for c in json.load(gzip.open(FRA))['cards']}
    rar.update(fra)
    f = pd.read_csv(R / 'c9_power_questions/c9_features.csv.gz')
    f['rar'] = f['key'].map(rar)
    g = f.groupby('id').agg(rar=('rar', 'max'), sd=('c9_s_GRADE', 'first'), m=('c9_m_GRADE', 'first')).reset_index()
    g = g.merge(u[['id', 'auto']], on='id')
    g = g[g['auto'] == 0].copy()
    g['rar'] = g['rar'].fillna(0)
    g['cls'] = np.where(g['rar'] >= 2, 'R', 'C')
    g['target'] = ((g['rar'] >= 2) | (g['sd'] >= SD_MIN)).astype(int)
    return g, u


def ladder():
    p = pd.read_csv(R / 'fin_final/fin_predictions.csv.gz')
    c = pd.read_csv(R / 'fin_final/c3_cards_fin.csv.gz', keep_default_na=False)
    c['name'] = c['keys'].str.split('|', n=1).str[1]
    d = p.merge(c[['name', 'type_line', 'btext', 'mv', 'colors', 'pt', 'auto']], on='name')
    d = d[(d['auto'] == 0) & (d['gih_games'] >= 1500) & (d['btext'].str.len() <= MAXLEN) & (~d['type_line'].str.contains('Basic'))]
    res = {}
    for cls, mask in (('C', d['rarity_ord'] <= 1), ('R', d['rarity_ord'] >= 2)):
        x = d[mask].copy()
        allx = p[(p['rarity_ord'] <= 1) if cls == 'C' else (p['rarity_ord'] >= 2)]
        x['pct'] = x['actual_gih'].apply(lambda v: (allx['actual_gih'] < v).mean() * 100)
        rows, used = [], set()
        for q in QS:
            y = x[~x['name'].isin(used)].assign(dist=lambda t: (t['pct'] - q).abs()).sort_values(['dist', 'gih_games'], ascending=[True, False]).iloc[0]
            used.add(y['name']); rows.append(y)
        res[cls] = rows
    return res


def render(cardrow):
    r = cardrow
    cl = r['colors'] if r['colors'] else 'colourless'
    pt = f" {r['pt']}" if r['pt'] not in ('', '0', 0) else ''
    return f"MV {r['mv']} {cl} | {r['type_line']}{pt}\n{r['btext']}"


def main():
    g, u = targets()
    blk = blocks()
    g.to_csv(HERE / 'targets.csv', index=False)
    L = ladder()
    lad = {}
    for cls in 'CR':
        lad[cls] = [{'level': i + 1, 'pct': QS[i], 'name': r['name'], 'actual_gih': round(float(r['actual_gih']), 4), 'text': render(r)} for i, r in enumerate(L[cls])]
    json.dump(lad, open(HERE / 'ladder.json', 'w'), indent=1, ensure_ascii=False)
    # inputs: two passes, different order, batches of BATCH within class
    for p in ('r1', 'r2'):
        (HERE / 'input' / p).mkdir(parents=True, exist_ok=True)
    t = g[g['target'] == 1]
    n = 0
    for cls in 'CR':
        ids = sorted(t.loc[t['cls'] == cls, 'id'])
        for p, seed in (('r1', 11), ('r2', 29)):
            order = list(ids)
            random.Random(seed + (cls == 'R')).shuffle(order)
            for b in range(0, len(order), BATCH):
                chunk = order[b:b + BATCH]
                name = f"{cls}{b // BATCH:02d}.txt"
                body = '\n\n'.join(re.sub(r'^(#\d+) \| ', r'\1 | ', blk[i]) for i in chunk)
                (HERE / 'input' / p / name).write_text(f"CLASS {cls}\n\n{body}\n-- {name[:-4]}, pass {p}: {len(chunk)} cards\n")
                n += 1
    print('targets', len(t), t['cls'].value_counts().to_dict(), 'batches', n)


if __name__ == '__main__':
    main()
