#!/usr/bin/env python3
"""B11g export for a set that is not out yet (TRK), from the official-gallery card list (the file the Pages site reads).

B11g = B10 with C9 replaced by G3 (research/g3_retrain, 28-set LOSO PASS; adopted for TRK by the user 2026-10-28).
Writes the two files that limited-forecast-pages/scripts/build-set-forecast.mjs reads (same schema as export_b10.py):
  adopted-gih.json.gz   per-card B11g GIH WR and the structured/text split
  gih-range.json        80% range (method M5 unchanged, refit on the 28-set leave-one-set-out B11g residuals)
and, with --explain, the per-card contributions that reasons_b11g.py turns into the one-line reason (local only, not published):
  <explain>             structured part: SHAP per feature; text part: Ridge coefficient x TF-IDF per n-gram; both in final pp

  python3 export_b11g.py --cards <pages>/data/trk/target.json.gz --out-dir <pages>/data/trk [--set TRK] [--explain export_tmp/trk_b11g_explain.json.gz]

Labels: C3, C4, C5 (Sonnet) from label/cards.csv.gz by card name; C9 is not used.
G3: research/g3_expert_grade/TRK_full/pass{1,2,3}.json (Opus, build_trk.py) via keys_trk/TRK.csv; g3 = mean of the 3 passes,
g3_z = within-set z-score, cards not judged (basic lands, blank text) are filled like training (research/g3_retrain/b11.py).
Spread (B10S-style factor): Rule F22 arm S on the B11g OOF is NOT supported (research/g3_retrain/spread_b11g.json: gain 0.004pp < 0.01pp),
so no factor is applied by default; --spread applies the 28-set factor anyway (user decision).
FIN, MH3, FRA outcomes are not used. MTGAZone's TRK review is not used.
"""
import argparse, gzip, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parents[0]
for p in ('g3_retrain', 'c9_power_questions', 'gih_llm_extract'):
    sys.path.insert(0, str(R / p))
sys.path.insert(0, str(HERE))
import b11  # noqa: E402
import c3_research as c3  # noqa: E402
import trk_label as t  # noqa: E402
c9 = b11.c9
c5, e = c9.c5, c9.e

VERSION = 'gih-b11g-28set-20261029-trk-preview'
G3 = R / 'g3_expert_grade'
OOF_B11G = R / 'g3_retrain/oof_B11g.csv.gz'
SPREAD = json.loads((R / 'g3_retrain/spread_b11g.json').read_text())
G3_PASSES = 3


def g3_for(rows, code):
    """g3 (mean of the passes) and g3_z per row; rows not judged get the training fill (b11.run_arm)."""
    key = pd.read_csv(G3 / 'keys_trk' / f'{code}.csv')
    passes = [json.load(open(G3 / f'{code}_full' / f'pass{k}.json')) for k in range(1, G3_PASSES + 1)]
    for k, d in enumerate(passes, 1):
        if set(d) != set(key.tid):
            raise SystemExit(f'G3 pass{k} does not cover exactly the targets in keys_trk/{code}.csv')
    key['g3'] = np.mean([key.tid.map(d).astype(float) for d in passes], axis=0)
    key['g3_z'] = (key.g3 - key.g3.mean()) / key.g3.std()
    by = {t.norm_name(n): (g, z) for n, g, z in zip(key.name, key.g3, key.g3_z)}
    m = float(key.g3.mean())
    judged = [t.norm_name(r.name) in by for r in rows]
    if any(not j and not r.auto for j, r in zip(judged, rows)):
        raise SystemExit('G3 missing for labelled non-automatic cards (rebuild with build_trk.py and judge again)')
    # training filled both g3 and g3_z of unjudged cards with the set mean of g3 (b11.run_arm); kept identical
    g = np.array([by[t.norm_name(r.name)][0] if j else m for j, r in zip(judged, rows)])
    z = np.array([by[t.norm_name(r.name)][1] if j else m for j, r in zip(judged, rows)])
    agree = [float(np.corrcoef(key.tid.map(passes[a]).astype(float), key.tid.map(passes[b]).astype(float))[0, 1])
             for a, b in ((0, 1), (0, 2), (1, 2))]
    return g, z, {'targets': len(key), 'pass_pearson': [round(x, 3) for x in agree], 'mean': round(m, 4)}


def fit_seed(train, test, nums, seed):
    """e.parts (research/production_c3/export_gih_c3_28set.py) with the fitted models kept, for the contributions."""
    from sklearn.ensemble import ExtraTreesRegressor
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    y = train['actual_gih']
    tree = make_pipeline(SimpleImputer(strategy='median'),
                         ExtraTreesRegressor(n_estimators=600, min_samples_leaf=8, max_features=.6, n_jobs=-1, random_state=seed))
    tree.fit(train[nums], y)
    text = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=12000, sublinear_tf=True), Ridge(alpha=10))
    text.fit(train['__text'], y)
    return float(y.mean()), tree, text


def contributions(tree, text, test, nums):
    """Structured: SHAP values of the tree part per feature; text: coef x tfidf per n-gram. Both add up to that part's prediction."""
    import shap
    imp, et = tree.steps[0][1], tree.steps[1][1]
    xs = imp.transform(test[nums])
    ex = shap.TreeExplainer(et)
    sv = ex.shap_values(xs, check_additivity=False)
    base_t = float(np.ravel(ex.expected_value)[0])
    vec, rg = text.steps[0][1], text.steps[1][1]
    m = vec.transform(test['__text']).tocsr()
    words = vec.get_feature_names_out()
    tw = []
    for i in range(m.shape[0]):
        row = m.getrow(i)
        tw.append({words[j]: float(v * rg.coef_[j]) for j, v in zip(row.indices, row.data)})
    return sv, base_t, tw, float(rg.intercept_)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cards', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--set', default='TRK')
    ap.add_argument('--spread', action='store_true', help='apply the B11g 28-set spread factor (not supported by Rule F22)')
    ap.add_argument('--explain', type=Path, help='write per-card contributions (local, not published)')
    ap.add_argument('--check', action='store_true', help='also run e.predict and require identical predictions')
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
        if not r.auto and not all(r.id in raws[p] for p in ('c3', 'c4', 'c5')):
            raise SystemExit(f'labels incomplete for {r.name}')
    t3, t4, t5, _ = t.label_tables(rows, raws, with_c9=False)
    g3, g3z, g3meta = g3_for(rows, code)

    x = pd.DataFrame([r.auto == 1 and [0] * 10 + ['-'] or raws['c3'][r.id] for r in rows], columns=c3.FIELDS + ['dep'])
    c3csv = pd.concat([pd.DataFrame({'key': [f"{code}|{c['id']}" for c in gal]}), x, t3], axis=1)
    tmp = HERE / 'export_tmp'
    tmp.mkdir(exist_ok=True)
    c3path = tmp / f'c3_{code.lower()}_gallery.csv.gz'
    c3csv.to_csv(c3path, index=False, compression='gzip')

    pool, base, cols = c9.load_pool()
    pool = pool.merge(b11.g3_table(), on='key', how='left')
    assert pool.g3.isna().mean() < 0.01
    pool[['g3', 'g3_z']] = pool[['g3', 'g3_z']].fillna(pool.groupby('set').g3.transform('mean')).fillna(0)
    fra, f = e.fra_frame(a.cards, base, cols, pool, code, c3path)
    for tab in (t4, t5):
        for c in tab.columns:
            f[c] = tab[c].to_numpy(dtype=float)
    f['g3'], f['g3_z'] = g3, g3z
    nums = c5.arm_nums('B5', base, cols) + ['g3', 'g3_z']  # = b11.run_arm('B11g')

    fits = [fit_seed(pool, f, nums, sd) for sd in c9.SEEDS]
    c = fits[0][0]
    tr = np.mean([m[1].predict(f[nums]) for m in fits], axis=0)
    tx = np.mean([m[2].predict(f['__text']) for m in fits], axis=0)
    p = np.mean([c + 1.25 * (.7 * m[1].predict(f[nums]) + .3 * m[2].predict(f['__text']) - c) for m in fits], axis=0)
    if a.check:
        c_, tr_, tx_, p_ = e.predict(pool, f, nums)
        assert abs(c - c_) < 1e-12 and np.allclose(p, p_, atol=1e-12, rtol=0), 'fit_seed differs from e.predict'
        print('check: identical to e.predict', flush=True)
    b = SPREAD['b_all28'] if a.spread else 1.0
    m = float(np.mean(p))
    p = m + b * (p - m)
    sd_, td_ = b * 1.25 * .7 * (tr - c) * 100, b * 1.25 * .3 * (tx - c) * 100
    spread_txt = (f'予測の広がりを過去28セットの実測に合わせて広げる補正（セット平均からの差を{b:.3f}倍）を加えています。' if a.spread else '')
    out = {
        'version': VERSION + ('-s' if a.spread else ''), 'set': code, 'preliminary': True,
        'source_repository': 'meatgoodbyeeee-wq/17lands-limited-forecast-data', 'source_head': e.head(),
        'fin_used': False, 'mh3_used': False, 'mtgazone_trk_used': False, 'training_sets': sorted(set(pool['set'])),
        'method': ('B11g: ExtraTrees 600 leaf 8 max_features 0.6 on baseline + C3 + C4 + C5 + G3 features (+ word TF-IDF Ridge alpha 10); 70:30; '
                   'fixed 1.25; seeds 20260922-24 averaged' + (f'; spread x{b:.4f} around the set mean' if a.spread else '; no spread factor')),
        'features': 'baseline pre-release card features + AI-read C3 effects, C4 fine effects, C5 atomic tags, G3 expert-style grade '
                    '(research/g3_expert_grade; replaces C9, research/g3_retrain PASS on 28 sets)',
        'labellers': 'C3, C4, C5: Sonnet; G3: Opus, 3 passes averaged (whole set in view)',
        'g3': g3meta, 'spread_factor': b,
        'texts': {  # wording the Pages site shows for this model (lib/adopted-gih-core.mjs)
            'structured_label': '構造化特徴量（AI抽出の効果・評価を含む）',
            'summary': '28セット（KHM〜HOB、FIN・MH3を除く）の発売前特徴量と、AIがルールテキストから読み取ったカード効果（C3〜C5）、'
                       '過去の専門家の評価を手本にAIがセット全体を見て付けた評価（G3）から、構造化特徴量のExtraTreesとルールテキストの'
                       'TF-IDF/Ridgeを70:30で合成し、固定係数で予測しています。' + spread_txt + 'プレビュー中の暫定版です。',
            'note': 'GIH WR：28セットの構造化特徴量（AIが読み取ったカード効果と、専門家の評価を手本にしたAIの評価を含む）＋ルールテキスト予測'
                    + ('＋予測の広がり補正' if a.spread else '') + '（暫定）。ALSAは従来の予測モデル。'},
        'seeds': c9.SEEDS, 'base': round(c * 100, 5),
        'cards': [{'id': card['id'], 'name': card['name'], 'oracle_text': card.get('oracle_text') or '', 'type_line': card.get('type_line') or '',
                   'mana_cost': card.get('mana_cost') or '', 'gih': round(float(pp * 100), 6), 'structured_delta': round(float(s), 6),
                   'text_delta': round(float(tt), 6)} for card, pp, s, tt in zip(fra, p, sd_, td_)],
    }
    a.out_dir.mkdir(parents=True, exist_ok=True)
    adopted_path = a.out_dir / 'adopted-gih.json.gz'
    with gzip.open(adopted_path, 'wt', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False)
    s = pd.Series(p * 100)
    print(json.dumps({'cards': len(fra), 'base': out['base'], 'spread': b, 'g3': g3meta, 'gih_min': round(s.min(), 2),
                      'gih_median': round(s.median(), 2), 'gih_max': round(s.max(), 2), 'gih_sd': round(s.std(), 2)}), flush=True)

    if a.explain:
        sv, tw, tb, ti = [], [], [], []
        for _, tree, text in fits:
            v, bt, w, it = contributions(tree, text, f, nums)
            sv.append(v); tb.append(bt); tw.append(w); ti.append(it)
        k = b * 1.25 * 100 / len(fits)  # final pp per unit of one seed's part prediction
        struct = sum(v for v in sv) * .7 * k
        words = []
        for i in range(len(fra)):
            d = {}
            for w in tw:
                for g, v in w[i].items():
                    d[g] = d.get(g, 0.) + v * .3 * k
            words.append(d)
        const = float(m * 100 * (1 - b) + b * 100 * (c + 1.25 * (.7 * (np.mean(tb) - c) + .3 * (np.mean(ti) - c))))
        recon = const + struct.sum(1) + np.array([sum(d.values()) for d in words])
        err = float(np.abs(recon - p * 100).max())
        ex = {'version': out['version'], 'set': code, 'unit': 'final GIH WR pp', 'constant': const, 'max_reconstruction_error_pp': err,
              'features': nums,
              'cards': [{'id': card['id'], 'name': card['name'], 'gih': float(pp * 100), 'values': {n: float(f[n].iloc[i]) for n in nums},
                         'structured': [float(z) for z in struct[i]], 'text': {g: v for g, v in words[i].items() if abs(v) > 1e-6}}
                        for i, (card, pp) in enumerate(zip(fra, p))]}
        a.explain.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(a.explain, 'wt', encoding='utf-8') as fh:
            json.dump(ex, fh, ensure_ascii=False)
        print(json.dumps({'explain': str(a.explain), 'max_reconstruction_error_pp': err}), flush=True)

    # range: production range code with the B11g out-of-fold residuals
    pool_t = pool[['set', 'name', 'type_line']].drop_duplicates(['set', 'name'])
    o = pd.read_csv(OOF_B11G).merge(pool_t, on=['set', 'name'], how='left', validate='one_to_one')
    o['pred'] = o.groupby('set')['pred'].transform(lambda x: x.mean() + b * (x - x.mean()))
    assert o['type_line'].notna().all()
    oof = tmp / 'oof_b11g_for_range.csv.gz'
    o[['set', 'name', 'rarity_ord', 'type_line', 'actual_gih', 'pred']].to_csv(oof, index=False, compression='gzip')
    e.OOF = oof
    ns = argparse.Namespace(fra=a.cards, set=code, c3=c3path, version=out['version'], adopted=adopted_path, out=a.out_dir / 'gih-range.json')
    e.cmd_range(ns)


if __name__ == '__main__':
    main()
