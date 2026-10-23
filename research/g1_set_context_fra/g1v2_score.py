#!/usr/bin/env python3
"""G1 plan v2: FRA scoring (PLAN_v2.md 7.3, F1-F3, P4 on FRA). Run ONCE on the final 28-day FRA data, after fra_frozen_v2.csv/.json are committed.

  python3 g1v2_score.py --actual <fra-public-game.json | csv with name,gih[,gih_n]> [--min-games 500]
  python3 g1v2_score.py --selftest      # synthetic frozen file + synthetic actuals in a temp dir; checks the code path only

Frozen file fra_frozen_v2.csv (written by the freeze step, 8) must have the columns
  id, name, pred_arm0 (= frozen B10, equals pred_B10 of research/c9_power_questions/fra_frozen_predictions.csv),
  pred_v2 (after the old/new scale conversion), pred_v2_raw (without conversion), has_setinfo (0/1),
  old_GRADE, new_GRADE_conv, new_GRADE_raw   [optional: old_<Q>, new_conv_<Q> for the 7 questions Q = IMP UNA VAL FLOOR FLEX PLAY GRADE]
fra_frozen_v2.json must hold its sha256. The script refuses to run if the hash differs or if eval_v2/past_gate.json is missing / not all_pass.
Never refits anything; the actual file is read only here.
"""
import argparse, hashlib, json, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'c9_power_questions' / 'fra_frozen_predictions.csv'
BOOT, SEED = 10000, 20261028
HOT, BASE_PP = 0.5, 0.05


def load_actual(path, min_games):
    path = Path(path)
    if path.suffix == '.csv':
        d = pd.read_csv(path)
    else:
        j = json.loads(path.read_text())
        cards = (j.get('observations') or j)['cards'] if isinstance(j, dict) else j
        d = pd.DataFrame(cards)
    if 'gih_n' in d and min_games:
        d = d[d['gih_n'] >= min_games]
    return d[['name', 'gih']].rename(columns={'gih': 'actual'}).assign(actual=lambda x: x.actual / (100 if x.actual.max() > 1.5 else 1))


def metrics(df, col):
    d = df[col] - df['actual']
    rank = df['actual'].rank(ascending=False, method='first')
    return {'mae': float(d.abs().mean() * 100), 'spearman': float(spearmanr(df[col], df['actual']).correlation),
            'under_top10': float(-d[rank <= 10].mean() * 100), 'under_top20': float(-d[rank <= 20].mean() * 100)}


def boot_ci(df, c0, c1, rng, boot):
    n = len(df)
    out = {k: [] for k in ('dmae', 'dspear', 'dtop10', 'dtop20')}
    for _ in range(boot):
        s = df.iloc[rng.integers(0, n, n)]
        a, b = metrics(s, c0), metrics(s, c1)
        out['dmae'].append(b['mae'] - a['mae']); out['dspear'].append(b['spearman'] - a['spearman'])
        out['dtop10'].append(b['under_top10'] - a['under_top10']); out['dtop20'].append(b['under_top20'] - a['under_top20'])
    return {k: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))] for k, v in out.items()}


def verify(frozen_dir, selftest):
    f, j = Path(frozen_dir) / 'fra_frozen_v2.csv', Path(frozen_dir) / 'fra_frozen_v2.json'
    meta = json.loads(j.read_text())
    assert hashlib.sha256(f.read_bytes()).hexdigest() == meta['sha256'], 'fra_frozen_v2.csv changed after freezing'
    gate = HERE / 'eval_v2' / 'past_gate.json'
    if not selftest:
        assert gate.exists(), 'eval_v2/past_gate.json missing: run g1v2_eval.py on the past sets first'
        g = json.loads(gate.read_text())
        assert g.get('all_pass') and not g.get('selftest'), f'past-set gate not passed: {g}'
    return pd.read_csv(f)


def selftest_frozen():
    d = Path(tempfile.mkdtemp(prefix='g1v2_score_selftest_'))
    rng = np.random.default_rng(1)
    b = pd.read_csv(BASE)
    df = b[['id', 'name']].copy()
    df['pred_arm0'] = b.pred_B10
    df['pred_v2'] = b.pred_B10 + rng.normal(0, 0.005, len(b))
    df['pred_v2_raw'] = df.pred_v2 + rng.normal(0, 0.003, len(b))
    df['has_setinfo'] = (rng.random(len(b)) < 0.15).astype(int)
    df['old_GRADE'] = rng.uniform(2, 8, len(b))
    df['new_GRADE_conv'] = df.old_GRADE + rng.normal(0, 0.7, len(b))
    df['new_GRADE_raw'] = df.new_GRADE_conv + 0.5
    df.to_csv(d / 'fra_frozen_v2.csv', index=False)
    (d / 'fra_frozen_v2.json').write_text(json.dumps({'sha256': hashlib.sha256((d / 'fra_frozen_v2.csv').read_bytes()).hexdigest()}))
    act = b[['name']].assign(gih=(b.pred_B10 + rng.normal(0, 0.03, len(b))) * 100, gih_n=rng.integers(300, 3000, len(b)))
    act.to_csv(d / 'actual.csv', index=False)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--actual'); ap.add_argument('--min-games', type=int, default=500)
    ap.add_argument('--frozen-dir', default=str(HERE)); ap.add_argument('--out-dir', default=str(HERE / 'eval_v2'))
    ap.add_argument('--boot', type=int, default=BOOT); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    out = Path(a.out_dir)
    if a.selftest:
        d = selftest_frozen()
        a.frozen_dir, a.actual, a.boot = str(d), str(d / 'actual.csv'), min(a.boot, 300)
        out = Path(tempfile.mkdtemp(prefix='g1v2_score_out_'))
        print('SELFTEST: synthetic frozen file and actuals in', d, '- results mean nothing')
    out.mkdir(parents=True, exist_ok=True)
    fz = verify(a.frozen_dir, a.selftest)
    if not a.selftest:
        base = pd.read_csv(BASE).set_index('id')
        assert np.allclose(fz.set_index('id').pred_arm0, base.loc[fz.id, 'pred_B10'].to_numpy()), 'pred_arm0 differs from the frozen B10'
    act = load_actual(a.actual, a.min_games)
    unmatched = sorted(set(act['name']) - set(fz['name']))
    df = fz.merge(act, on='name')
    print(f'scored cards {len(df)}, unmatched actual names {len(unmatched)} {unmatched[:5]}')
    rng = np.random.default_rng(SEED)
    res = {'n': len(df), 'arm0': metrics(df, 'pred_arm0')}
    for col in ('pred_v2', 'pred_v2_raw'):
        m = metrics(df, col)
        d = {k: m[k] - res['arm0'][k] for k in m}
        res[col] = {**m, 'delta': d, 'ci95': boot_ci(df, 'pred_arm0', col, rng, a.boot)}
    c = res['pred_v2']['delta']
    F1, F2, F3 = c['mae'] <= 0, (c['under_top20'] < 0 and c['under_top10'] <= 0), c['spearman'] >= 0
    # P4 on FRA: converted GRADE up >= +0.5 -> share with actual below the set mean
    df['grade_move'] = df.new_GRADE_conv - df.old_GRADE
    below = df.actual <= df.actual.mean()
    hot = df.grade_move >= HOT
    base_rate = float(below.mean())
    p4 = {'base_rate': base_rate, 'n_moved_up': int(hot.sum()), 'share_below_avg': float(below[hot].mean()) if hot.sum() else None,
          'fail': bool(hot.sum() and below[hot].mean() > base_rate + BASE_PP)}
    res['P4_fra'] = p4
    # split by SET INFO
    for name, m in (('setinfo', df.has_setinfo == 1), ('no_setinfo', df.has_setinfo == 0)):
        s = df[m]
        res[f'split_{name}'] = {'n': int(len(s)), 'mae_arm0': float((s.pred_arm0 - s.actual).abs().mean() * 100),
                                'mae_v2': float((s.pred_v2 - s.actual).abs().mean() * 100), 'mean_grade_move': float(s.grade_move.mean())}
    res['verdict'] = {'F1_mae_not_worse': bool(F1), 'F2_top20_shrinks_top10_not_larger': bool(F2), 'F3_spearman_not_worse': bool(F3),
                      'P4_fra_reported': p4, 'adopt_proposal': bool(F1 and F2 and F3)}
    moves = df.copy()
    moves['pred_change_pp'] = (moves.pred_v2 - moves.pred_arm0) * 100
    moves['err_arm0_pp'] = (moves.pred_arm0 - moves.actual) * 100
    moves['err_v2_pp'] = (moves.pred_v2 - moves.actual) * 100
    moves = moves[moves.grade_move.abs() >= HOT].sort_values('grade_move', ascending=False)
    (out / 'fra_score_v2.json').write_text(json.dumps(res, indent=1, default=float))
    moves.to_csv(out / 'grade_moves_v2.csv', index=False)
    df.to_csv(out / 'fra_score_cards_v2.csv', index=False)
    print(json.dumps(res, indent=1, default=float))
    print('outputs in', out)


if __name__ == '__main__':
    main()
