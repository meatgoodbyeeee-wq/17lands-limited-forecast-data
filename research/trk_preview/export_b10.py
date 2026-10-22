#!/usr/bin/env python3
"""B10 preview export for a set that is not out yet, from the official-gallery card list (the file the Pages site reads).

Writes the two files that limited-forecast-pages/scripts/build-set-forecast.mjs reads (same schema as research/production_c3):
  adopted-gih.json.gz   per-card B10 GIH WR and the structured/text split
  gih-range.json        80% range (method M5 unchanged, refit on the 28-set leave-one-set-out B10 residuals)

  python3 export_b10.py --cards <pages>/data/trk/target.json.gz --out-dir <pages>/data/trk [--set TRK]

Labels (C3, C4, C5, C9 x3) are found by card name in label/cards.csv.gz, so the gallery list and the Scryfall list share one label set.
Cards with no label stop the export (queue and label them with trk_label.py first). Preliminary: the preview version string says so.
FIN, MH3, FRA outcomes are not used.
"""
import argparse, gzip, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parents[0]
sys.path.insert(0, str(R / 'c9_power_questions'))
sys.path.insert(0, str(R / 'gih_llm_extract'))
sys.path.insert(0, str(HERE))
import c9  # noqa: E402
import c3_research as c3  # noqa: E402
import trk_label as t  # noqa: E402
c5, e = c9.c5, c9.e

VERSION = 'gih-b10-28set-20260929-trk-preview'
OOF_B10 = R / 'c9_power_questions/oof_B10.csv.gz'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cards', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--set', default='TRK')
    a = ap.parse_args()
    code = a.set.upper()
    gal = json.loads(gzip.open(a.cards, 'rt', encoding='utf-8').read())['cards']
    q = pd.read_csv(t.LAB / 'cards.csv.gz', keep_default_na=False)
    byname = {}
    for r in q.itertuples():
        byname.setdefault(t.norm_name(r.name), r)
    miss = [c['name'] for c in gal if t.norm_name(c['name']) not in byname]
    if miss:
        raise SystemExit(f'no labels for {len(miss)} gallery cards: {miss[:20]}')
    rows = [byname[t.norm_name(c['name'])] for c in gal]
    raws = {p: d for p, (d, bad) in t.load_all().items()}
    for r in rows:
        if not r.auto and not all(r.id in raws[p] for p in t.PASSES):
            raise SystemExit(f'labels incomplete for {r.name}')
    t3, t4, t5, t9 = t.label_tables(rows, raws)

    # C3 csv keyed like the production file so export.fra_frame / cmd_range can read it
    x = pd.DataFrame([r.auto == 1 and [0] * 10 + ['-'] or raws['c3'][r.id] for r in rows], columns=c3.FIELDS + ['dep'])
    c3csv = pd.concat([pd.DataFrame({'key': [f"{code}|{c['id']}" for c in gal]}), x, t3], axis=1)
    tmp = HERE / 'export_tmp'
    tmp.mkdir(exist_ok=True)
    c3path = tmp / f'c3_{code.lower()}_gallery.csv.gz'
    c3csv.to_csv(c3path, index=False, compression='gzip')

    pool, base, cols = c9.load_pool()
    fra, f = e.fra_frame(a.cards, base, cols, pool, code, c3path)
    for tab in (t4, t5, t9):
        for c in tab.columns:
            f[c] = tab[c].to_numpy(dtype=float)
    nums = c5.arm_nums('B5', base, cols) + c9.MEAN + c9.SD + c9.SUM
    c, tr, tx, p = e.predict(pool, f, nums)
    sd_, td_ = 1.25 * .7 * (tr - c) * 100, 1.25 * .3 * (tx - c) * 100
    out = {
        'version': VERSION, 'set': code, 'preliminary': True,
        'source_repository': 'meatgoodbyeeee-wq/17lands-limited-forecast-data', 'source_head': e.head(),
        'fin_used': False, 'mh3_used': False, 'training_sets': sorted(set(pool['set'])),
        'method': 'B10: ExtraTrees 600 leaf 8 max_features 0.6 on baseline + C3 + C4 + C5 + C9 features (+ word TF-IDF Ridge alpha 10); 70:30; fixed 1.25; seeds 20260922-24 averaged',
        'features': 'baseline pre-release card features + AI-read C3 effects, C4 fine effects, C5 atomic tags, C9 power questions x3 passes (research/c9_power_questions, Rule F10 passed on 28 sets)',
        'labellers': 'C3, C4, C5: Sonnet; C9 passes 1-3: Opus (research/trk_preview/RESULTS.md Step 1)',
        'texts': {  # wording the Pages site shows for this model (lib/adopted-gih-core.mjs)
            'structured_label': '構造化特徴量（AI抽出の効果・強さ判定を含む）',
            'summary': '28セット（KHM〜HOB、FIN・MH3を除く）の発売前特徴量と、AIがルールテキストから読み取ったカード効果・強さの判定（C3〜C5・C9）から、構造化特徴量のExtraTreesとルールテキストのTF-IDF/Ridgeを70:30で合成し、固定係数で予測しています。プレビュー中の暫定版です。',
            'note': 'GIH WR：28セットの構造化特徴量（AIが読み取ったカード効果と強さの判定を含む）＋ルールテキスト予測（暫定）。ALSAは従来の予測モデル。'},
        'seeds': e.SEEDS, 'base': round(c * 100, 5),
        'cards': [{'id': card['id'], 'name': card['name'], 'oracle_text': card.get('oracle_text') or '', 'type_line': card.get('type_line') or '',
                   'mana_cost': card.get('mana_cost') or '', 'gih': round(float(pp * 100), 6), 'structured_delta': round(float(s), 6),
                   'text_delta': round(float(tt), 6)} for card, pp, s, tt in zip(fra, p, sd_, td_)],
    }
    a.out_dir.mkdir(parents=True, exist_ok=True)
    adopted_path = a.out_dir / 'adopted-gih.json.gz'
    with gzip.open(adopted_path, 'wt', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False)
    s = pd.Series(p * 100)
    print(json.dumps({'cards': len(fra), 'base': out['base'], 'gih_min': round(s.min(), 2), 'gih_median': round(s.median(), 2),
                      'gih_max': round(s.max(), 2), 'gih_sd': round(s.std(), 2)}))

    # range: production range code with the B10 out-of-fold residuals
    pool_t = pool[['set', 'name', 'type_line']].drop_duplicates(['set', 'name'])
    o = pd.read_csv(OOF_B10).merge(pool_t, on=['set', 'name'], how='left', validate='one_to_one')
    assert o['type_line'].notna().all()
    oof = tmp / 'oof_b10_for_range.csv.gz'
    o[['set', 'name', 'rarity_ord', 'type_line', 'actual_gih', 'pred']].to_csv(oof, index=False, compression='gzip')
    e.OOF = oof
    ns = argparse.Namespace(fra=a.cards, set=code, c3=c3path, version=VERSION, adopted=adopted_path, out=a.out_dir / 'gih-range.json')
    e.cmd_range(ns)


if __name__ == '__main__':
    main()
