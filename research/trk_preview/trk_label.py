#!/usr/bin/env python3
"""TRK previewed cards: blinded queue -> labels (C3, C4, C5, C9 x3) -> B10 prediction. Research only (PLAN.md Step 2).

  python3 trk_label.py queue                 # data/trk_scryfall_raw.json.gz -> label/cards.csv.gz (+ label/input/<pass>.txt for NEW cards)
  python3 trk_label.py check                 # validate label/raw/<pass>.txt against the queue
  python3 trk_label.py predict               # B10 for every card with complete labels -> pred_b10.csv

Ids are fixed per card once assigned (label/ids.csv, append only), so labels are never redone and later previews only add cards.
Blinding and card view are the same as production (name -> "~", no set, rarity or numbers). Nothing reads 17Lands outcomes.
"""
import argparse, gzip, json, random, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parents[0]
sys.path.insert(0, str(R / 'gih_llm_extract'))
sys.path.insert(0, str(R / 'c9_power_questions'))
sys.path.insert(0, str(HERE))
import build_input as bi  # noqa: E402
import sonnet_check as sc  # noqa: E402  (parsers: parse(), formats)

LAB = HERE / 'label'
RAW = HERE / 'data/trk_scryfall_raw.json.gz'
PASSES = sc.PASSES
# B11g (TRK model from 2026-10-29) replaces C9 by G3: new batches are labelled for C3, C4, C5 only; earlier C9 labels stay as they are
LABEL_PASSES = ['c3', 'c4', 'c5']
SEED = 20261022


def text_of(c):
    faces = c.get('card_faces') or []
    return c.get('oracle_text') or '\n//\n'.join(f.get('oracle_text', '') for f in faces)


def type_of(c):
    faces = c.get('card_faces') or []
    return c.get('type_line') or ' // '.join(f.get('type_line', '') for f in faces)


def norm_name(n):
    import unicodedata
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', n.lower().replace('’', "'")).encode('ascii', 'ignore').decode())


def view_rows(gallery=None):
    cards = json.loads(gzip.open(RAW, 'rt', encoding='utf-8').read())['cards']
    if gallery:  # official-gallery cards whose name is not in the Scryfall list yet (e.g. Stardates cards); same blinding
        have = {norm_name(c['name']) for c in cards}
        extra = [c for c in json.loads(gzip.open(gallery, 'rt', encoding='utf-8').read())['cards'] if norm_name(c['name']) not in have]
        cards = cards + extra
    rows = []
    for c in cards:
        ty, tx = bi.gallery_to_scryfall(type_of(c)), bi.gallery_to_scryfall(text_of(c))
        rows.append({'key': f"TRK|{c['id']}", 'name': c['name'], 'rarity': c.get('rarity'), 'type_line': ty, 'text': tx,
                     'mv': bi.fmt_num(c.get('cmc')), 'colors': ''.join(c.get('colors') or []),
                     'pt': '' if c.get('power') in (None, '') else f"{bi.fmt_num(c.get('power'))}/{bi.fmt_num(c.get('toughness'))}"})
    x = pd.DataFrame(rows)
    x['btext'] = [bi.blind(t, n, ty) for t, n, ty in zip(x['text'], x['name'], x['type_line'])]
    x['auto'] = np.where(x['type_line'].str.contains('Basic Land') | (x['btext'].str.strip() == ''), 1, 0)
    return x


def cmd_queue(a):
    LAB.mkdir(exist_ok=True)
    (LAB / 'input').mkdir(exist_ok=True)
    (LAB / 'raw').mkdir(exist_ok=True)
    x = view_rows(a.gallery)
    idf = LAB / 'ids.csv'
    old = pd.read_csv(idf, keep_default_na=False) if idf.exists() else pd.DataFrame(columns=['key', 'id', 'batch'])
    have = set(old['key'])
    oldq = pd.read_csv(LAB / 'cards.csv.gz', keep_default_na=False) if (LAB / 'cards.csv.gz').exists() else pd.DataFrame(columns=['name'])
    seen = {norm_name(n) for n in oldq['name']}
    new = x[~x['key'].isin(have) & ~x['name'].map(norm_name).isin(seen)].copy()
    batch = int(old['batch'].max()) + 1 if len(old) else 1
    rng = np.random.default_rng(SEED + batch)
    new = new.iloc[rng.permutation(len(new))]
    start = int(old['id'].max()) + 1 if len(old) else 1
    new['id'] = np.arange(start, start + len(new))
    new['batch'] = batch
    allids = pd.concat([old, new[['key', 'id', 'batch']]], ignore_index=True)
    allids.to_csv(idf, index=False)
    x = x.merge(allids, on='key')
    if len(oldq) and 'key' in oldq.columns:  # keep earlier rows whose key is no longer in the current list
        x = pd.concat([x, oldq[~oldq['key'].isin(x['key'])]], ignore_index=True)
    x.to_csv(LAB / 'cards.csv.gz', index=False, compression='gzip')
    todo = new[new['auto'] == 0]
    for p in LABEL_PASSES:
        cards = [sc.card_view(r, r.id) for r in todo.itertuples()]
        if p == 'c9p2':
            cards = cards[::-1]
        elif p == 'c9p3':
            random.Random(SEED + batch).shuffle(cards)
        (LAB / 'input' / f'b{batch:02d}_{p}.txt').write_text('\n\n'.join(cards) + f'\n-- batch {batch}, {p}: {len(cards)} cards\n')
    print({'batch': batch, 'new_cards': len(new), 'to_label': len(todo), 'auto': int((new['auto'] == 1).sum()), 'total': len(x)})


def load_all():
    out = {}
    for p in PASSES:
        d, bad = {}, []
        for f in sorted((LAB / 'raw').glob(f'b*_{p}.txt')):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if not line.strip():
                    continue
                r = sc.parse(p, line)
                if r is None or r[0] in d:
                    bad.append(f'{f.name}:{n} {line!r}'); continue
                d[r[0]] = r[1]
        out[p] = (d, bad)
    return out


def cmd_check(_a):
    q = pd.read_csv(LAB / 'cards.csv.gz', keep_default_na=False)
    need = set(q.loc[q['auto'] == 0, 'id'])
    ok = True
    for p, (d, bad) in load_all().items():
        print(p, 'labelled', len(d), 'missing', len(need - set(d)), 'extra', len(set(d) - need), 'errors', bad[:5])
        ok &= not (bad or (p in LABEL_PASSES and need - set(d)) or set(d) - need)  # C9 may be missing (not used by B11g)
    if not ok:
        raise SystemExit(1)


def label_tables(done, raws, with_c9=True):
    """C3/C4/C5/C9 feature tables (same construction as the production extractions) for rows with .id .auto .mv .type_line.
    with_c9=False: no C9 passes needed (B11g, where G3 replaces C9); t9 is then empty."""
    import c9
    c5 = c9.c5
    import c3_research as c3
    # C3
    rows = []
    for r in done:
        v = [0] * 10 + ['-'] if r.auto else raws['c3'][r.id]
        if r.auto and 'Creature' in r.type_line:
            v[2] = 1
        rows.append(v)
    x = pd.DataFrame(rows, columns=c3.FIELDS + ['dep'])
    t3 = c3.c3_columns(x, pd.Series([r.mv for r in done]))
    # C4, C5, C9
    t4r, t5r, t9r = [], [], []
    for r in done:
        if r.auto:
            v, role, sc5, tg = [0] * 14, 'O', [0, 0, 0], {}
            m, s = list(c9.MID), [0.0] * 7
        else:
            v, role = raws['c4'][r.id]
            sc5, tg = raws['c5'][r.id]
            if with_c9:
                a = np.array([raws[p][r.id] for p in ('c9p1', 'c9p2', 'c9p3')], float)
                m, s = a.mean(0).tolist(), a.std(0).tolist()
        t4r.append({**dict(zip(c5.C4_NUM, v)), **{f'c4_role_{k}': float(role == k) for k in 'ADVFRTSNO'}})
        d5 = {f'c5_{t}': tg.get(t, 0) for t in c5.cr.TAGS}
        d5.update(dict(zip(c5.SCALE, sc5)))
        d5['c5_ntags'] = len(tg); d5['c5_nlvl2'] = sum(1 for z in tg.values() if z == 2)
        d5['c5_ngroups'] = sum(any(t in tg for t in g.split()) for g in c5.GROUPS.values())
        t5r.append(d5)
        if not with_c9:
            continue
        d9 = dict(zip(c9.MEAN, m)); d9.update(dict(zip(c9.SD, s)))
        d9['c9_impuna'] = m[0] + m[1]; d9['c9_valfloor'] = m[2] + m[3]; d9['c9_bomb'] = m[6] - 1.25 * m[5]
        t9r.append(d9)
    t4, t5, t9 = pd.DataFrame(t4r), pd.DataFrame(t5r), pd.DataFrame(t9r)
    return t3, t4, t5, t9


def cmd_predict(_a):
    import c9
    c5, e = c9.c5, c9.e
    import c3_research as c3
    q = pd.read_csv(LAB / 'cards.csv.gz', keep_default_na=False)
    raws = {p: d for p, (d, bad) in load_all().items()}
    done = [r for r in q.itertuples() if r.auto == 1 or all(r.id in raws[p] for p in PASSES)]
    cards = {f"TRK|{c['id']}": c for c in json.loads(gzip.open(RAW, 'rt', encoding='utf-8').read())['cards']}
    done = [r for r in done if r.key in cards]  # Scryfall-listed cards only; the gallery list is handled by export_b10.py
    d = pd.DataFrame(done)
    keys = list(d['key'])
    t3, t4, t5, t9 = label_tables(done, raws)
    pool, base, cols = c9.load_pool()
    norm = [c3.normalize(cards[k]) for k in keys]
    f = pd.DataFrame([e.card_features(c) for c in norm])
    f['oracle_text'] = [c['oracle_text'] for c in norm]
    f['type_line'] = [c['type_line'] for c in norm]
    f['__text'] = e.g.text_of(f)
    for c in ('is_supplemental_power_set', 'is_premier_set'):
        if c not in f.columns:
            const = pool[c].dropna().unique()
            assert len(const) == 1
            f[c] = const[0]
    for c in cols:
        f[c] = t3[c].to_numpy(dtype=float)
    for t in (t4, t5, t9):
        for c in t.columns:
            f[c] = t[c].to_numpy(dtype=float)
    nums = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    p = e.predict(pool, f, nums)[3]
    out = pd.DataFrame({'key': keys, 'name': d['name'], 'rarity': d['rarity'], 'type_line': d['type_line'], 'mv': d['mv'],
                        'pred_b10': np.round(p * 100, 2), 'grade_mean': np.round(t9['c9_m_GRADE'], 2)})
    out = out[~out['type_line'].str.contains('Basic Land')].sort_values('pred_b10', ascending=False)
    out.to_csv(HERE / 'pred_b10.csv', index=False)
    print(len(out), 'cards; pred mean %.2f sd %.2f min %.2f max %.2f' % (out.pred_b10.mean(), out.pred_b10.std(), out.pred_b10.min(), out.pred_b10.max()))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for n, fn in (('queue', cmd_queue), ('check', cmd_check), ('predict', cmd_predict)):
        p = sub.add_parser(n); p.set_defaults(f=fn)
        if n == 'queue':
            p.add_argument('--gallery', type=Path, help='official-gallery target.json.gz; adds cards whose name is not known yet')
    a = ap.parse_args(); a.f(a)


if __name__ == '__main__':
    main()
