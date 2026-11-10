#!/usr/bin/env python3
"""TRK shadow forecasts (PLAN.md): arms G (published B11g), S (G with spread), T (B10, no spread), A = (T + G) / 2.

  python3 freeze.py --pages <limited-forecast-pages>          # writes trk_frozen.csv and frozen.json

G is read from the Pages file (not recomputed: the TRK G3 passes are not in this repository).
T follows research/trk_preview/export_b10.py up to e.predict, without the B10S spread factor.
Nothing here reads 17Lands outcomes of TRK, FRA, FIN or MH3.
"""
import argparse, gzip, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parents[0]
for p in ('c9_power_questions', 'gih_llm_extract', 'trk_preview'):
    sys.path.insert(0, str(R / p))
import c9  # noqa: E402
import c3_research as c3  # noqa: E402
import trk_label as t  # noqa: E402
c5, e = c9.c5, c9.e
SPREAD_B = json.loads((R / 'g3_retrain/spread_b11g.json').read_text())['b_all28']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def b10(cards_path, code='TRK'):
    gal = json.loads(gzip.open(cards_path, 'rt', encoding='utf-8').read())['cards']
    q = pd.read_csv(t.LAB / 'cards.csv.gz', keep_default_na=False)
    byname = {}
    for r in q.itertuples():
        byname.setdefault(t.norm_name(r.name), r)
    rows = [byname[t.norm_name(c['name'])] for c in gal]
    raws = {}
    for p, (d, bad) in t.load_all().items():
        assert not bad, (p, bad[:3])
        raws[p] = d
    for r in rows:
        assert r.auto or all(r.id in raws[p] for p in t.PASSES), f'labels incomplete for {r.name}'
    t3, t4, t5, t9 = t.label_tables(rows, raws)
    x = pd.DataFrame([r.auto == 1 and [0] * 10 + ['-'] or raws['c3'][r.id] for r in rows], columns=c3.FIELDS + ['dep'])
    c3csv = pd.concat([pd.DataFrame({'key': [f"{code}|{c['id']}" for c in gal]}), x, t3], axis=1)
    tmp = R / 'trk_preview/export_tmp'
    tmp.mkdir(exist_ok=True)
    c3path = tmp / 'c3_trk_shadow.csv.gz'
    c3csv.to_csv(c3path, index=False, compression='gzip')
    pool, base, cols = c9.load_pool()
    assert not {'TRK', 'FRA', 'FIN', 'MH3'} & set(pool['set'])
    fra, f = e.fra_frame(cards_path, base, cols, pool, code, c3path)
    for tab in (t4, t5, t9):
        for c in tab.columns:
            f[c] = tab[c].to_numpy(dtype=float)
    nums = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    p = e.predict(pool, f, nums)[3]
    return fra, p * 100, t9['c9_m_GRADE'].to_numpy(), sorted(set(pool['set']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', type=Path, required=True)
    a = ap.parse_args()
    cards_path, adopted_path = a.pages / 'data/trk/target.json.gz', a.pages / 'data/trk/adopted-gih.json.gz'
    adopted = json.loads(gzip.open(adopted_path, 'rt', encoding='utf-8').read())
    fra, tpred, grade, sets = b10(cards_path)
    assert [c['id'] for c in fra] == [c['id'] for c in adopted['cards']], 'card order differs from the published file'
    g = np.array([c['gih'] for c in adopted['cards']], float)
    m = float(g.mean())
    out = pd.DataFrame({'id': [c['id'] for c in fra], 'name': [c['name'] for c in fra], 'rarity': [c.get('rarity') for c in fra],
                        'G': np.round(g, 4), 'S': np.round(m + SPREAD_B * (g - m), 4), 'T': np.round(tpred, 4), 'A': np.round((tpred + g) / 2, 4),
                        'c9_grade_mean': np.round(grade, 3)})
    out.to_csv(HERE / 'trk_frozen.csv', index=False)
    labs = sorted((R / 'trk_preview/label/raw').glob('b*_c9p*.txt'))
    meta = {'frozen_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'cards': len(out),
            'trk_frozen_csv_sha256': sha(HERE / 'trk_frozen.csv'),
            'inputs': {'pages_target_json_gz': sha(cards_path), 'pages_adopted_gih_json_gz': sha(adopted_path), 'published_version': adopted['version'],
                       'c9_raw': {f.name: sha(f) for f in labs}},
            'spread_b': SPREAD_B, 'training_sets': sets, 'seeds': c9.SEEDS,
            'summary': {k: {'mean': round(float(out[k].mean()), 3), 'sd': round(float(out[k].std()), 3), 'min': round(float(out[k].min()), 2),
                            'max': round(float(out[k].max()), 2)} for k in 'GSTA'},
            'corr_T_G': round(float(np.corrcoef(out['T'], out['G'])[0, 1]), 4),
            'mean_abs_T_minus_G': round(float((out['T'] - out['G']).abs().mean()), 3)}
    (HERE / 'frozen.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: meta[k] for k in ('cards', 'trk_frozen_csv_sha256', 'summary', 'corr_T_G', 'mean_abs_T_minus_G')}, indent=1))


if __name__ == '__main__':
    main()
