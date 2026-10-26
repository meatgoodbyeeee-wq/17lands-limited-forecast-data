#!/usr/bin/env python3
"""Score extra PENDING_FRA items 11 (B10 spread correction S, Rule F22) and 12 (B10 M5 80% range coverage). Run once; nothing refitted.

  python3 research/fra_check/score_extra.py [--pages-dir /tmp/claude-0/pages] [--out research/fra_check/score_extra.json]

Frozen files are read with `git show <ref>:<path>` (the working-tree branch is not switched) and sha256-checked.
FRA actuals: research/fra_check/data/FRA_gih_28d.csv (card_name, gih_games, gih_wr_pct; >= 500 games; 10/17 file, post-hoc window).
Name matching as in score_pending.py: exact, else front face (text before " // ").
"""
import argparse, gzip, hashlib, io, json, subprocess
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
G2 = ('origin/research/g1-grade-diagnosis', 'research/g2_bias_spread/fra_frozen_predictions.csv', 'research/g2_bias_spread/fra_frozen_predictions.json')
RNG = ('origin/research/fra-b10-range', 'research/fra_b10_range/fra_b10_range.json', 'research/fra_b10_range/fra_b10_range.meta.json')
RARITY = 'research/gih_llm_extract/fra_frozen_predictions.csv'   # id,name,rarity (frozen, working tree)
C9 = 'research/c9_power_questions/fra_frozen_predictions.csv'


def show(ref, path):
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:{path}'], capture_output=True, check=True).stdout


def checked(spec, key='sha256'):
    ref, path, meta = spec
    b = show(ref, path); want = json.loads(show(ref, meta))[key]
    got = hashlib.sha256(b).hexdigest()
    if got != want:
        raise SystemExit(f'HASH MISMATCH {path}: {got} != {want}')
    return b, got


def front(n): return str(n).split(' // ')[0].strip()


def match(frozen_names, gih_names):
    fz = set(frozen_names); ff = {}
    for n in fz: ff.setdefault(front(n), []).append(n)
    m, fb, un = {}, [], []
    for g in gih_names:
        if g in fz: m[g] = g
        elif len(ff.get(front(g), [])) == 1: m[g] = ff[front(g)][0]; fb.append([g, m[g]])
        else: un.append(g)
    return m, fb, un


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages-dir', default='/tmp/claude-0/pages'); ap.add_argument('--out', default=str(ROOT / 'research/fra_check/score_extra.json'))
    a = ap.parse_args()
    g = pd.read_csv(ROOT / 'research/fra_check/data/FRA_gih_28d.csv')
    assert (g.gih_games >= 500).all() and not g.card_name.duplicated().any()
    gih = g.set_index('card_name')['gih_wr_pct']
    res = {'n_gih_cards': int(len(gih))}

    # ---- item 11
    b, h11 = checked(G2)
    d = pd.read_csv(io.BytesIO(b))
    c9 = pd.read_csv(ROOT / C9)
    assert np.allclose(d.set_index('id')['pred_B10'], c9.set_index('id')['pred_B10'].reindex(d['id']).values), 'pred_B10 differs between g2 file and c9 file'
    m, fb, un = match(d['name'], gih.index)
    dd = d.set_index('name'); rows = list(m.items())
    y = np.array([gih[x] for x, _ in rows]); p10 = np.array([dd.loc[f, 'pred_B10'] for _, f in rows]) * 100; pS = np.array([dd.loc[f, 'pred_B10S'] for _, f in rows]) * 100
    assert 30 < p10.mean() < 80 and 30 < pS.mean() < 80
    k = int(np.ceil(0.1 * len(y)))
    def met(p):
        yc, pc = y - y.mean(), p - p.mean()      # PLAN: set-centred pp
        top = np.argsort(-p)[:k]                   # predicted top 10% (within the matched FRA cards)
        return {'mae_centred_pp': float(np.mean(np.abs(yc - pc))), 'mae_raw_pp': float(np.mean(np.abs(y - p))),
                'spearman': float(spearmanr(p, y).correlation),
                'top10pct_mean_a_minus_p_centred': float(np.mean(yc[top] - pc[top])), 'top10pct_mean_a_minus_p_raw': float(np.mean(y[top] - p[top])), 'pred_sd_pp': float(p.std())}
    r10, rS = met(p10), met(pS)
    # slope of actual on predicted (centred), indicative
    slope = lambda p: float(np.polyfit(p - p.mean(), y - y.mean(), 1)[0])
    res['item11'] = {'sha256': h11, 'b': json.loads(show(G2[0], G2[2]))['b'], 'n_cards': len(rows), 'k_top10pct': k, 'B10': r10, 'B10S': rS,
                     'slope_actual_on_pred': {'B10': slope(p10), 'B10S': slope(pS)}, 'front_face_matches': fb, 'gih_not_in_frozen': un,
                     'S_beats_B10_mae_centred': rS['mae_centred_pp'] < r10['mae_centred_pp'], 'S_beats_B10_mae_raw': rS['mae_raw_pp'] < r10['mae_raw_pp']}

    # ---- item 12
    b, h12 = checked(RNG)
    R = json.loads(b)
    r = pd.DataFrame(R['cards'])[['id', 'name', 'radius']].rename(columns={'radius': 'r_b10'})
    A = json.load(gzip.open(Path(a.pages_dir) / 'data/adopted-gih-fra.json.gz', 'rt', encoding='utf-8'))
    P = json.load(open(Path(a.pages_dir) / 'data/gih-range-fra.json', encoding='utf-8'))
    assert A.get('version') == 'gih-c3-28set-20260929'
    prod = pd.DataFrame(A['cards'])[['id', 'name', 'gih']].merge(pd.DataFrame(P['cards'])[['id', 'radius']].rename(columns={'radius': 'r_prod'}), on='id', validate='one_to_one')
    rar = pd.read_csv(ROOT / RARITY)[['id', 'rarity']]
    t = r.merge(c9[['id', 'pred_B10']], on='id', validate='one_to_one').merge(prod[['id', 'gih', 'r_prod']], on='id', how='left', validate='one_to_one').merge(rar, on='id', how='left', validate='one_to_one')
    t['pred_B10'] *= 100
    m2, fb2, un2 = match(t['name'], gih.index)
    td = t.set_index('name'); rows = list(m2.items())
    T = td.loc[[f for _, f in rows]].copy(); T['actual'] = [gih[x] for x, _ in rows]
    T['in_b10'] = (T.actual - T.pred_B10).abs() <= T.r_b10
    T['in_prod'] = (T.actual - T.gih).abs() <= T.r_prod
    T['w_b10'] = 2 * T.r_b10; T['w_prod'] = 2 * T.r_prod
    def agg(s):
        return {'n': int(len(s)), 'cov_b10': float(s.in_b10.mean()), 'width_b10': float(s.w_b10.mean()), 'cov_prod': float(s.in_prod.mean()), 'width_prod': float(s.w_prod.mean())}
    res['item12'] = {'sha256': h12, 'q': R['q'], 'target': R['target_coverage'], 'overall': agg(T), 'by_rarity': {k_: agg(T[T.rarity == k_]) for k_ in ['common', 'uncommon', 'rare', 'mythic', 'land'] if (T.rarity == k_).any()},
                     'rarity_missing': int(T.rarity.isna().sum()), 'prod_missing': int(T.r_prod.isna().sum()), 'front_face_matches': fb2, 'gih_not_in_frozen': un2,
                     'pages_sha256': {f: hashlib.sha256((Path(a.pages_dir) / 'data' / f).read_bytes()).hexdigest() for f in ['adopted-gih-fra.json.gz', 'gih-range-fra.json']},
                     'b10_mae_raw_pp': float((T.actual - T.pred_B10).abs().mean()), 'prod_mae_raw_pp': float((T.actual - T.gih).abs().mean())}
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
