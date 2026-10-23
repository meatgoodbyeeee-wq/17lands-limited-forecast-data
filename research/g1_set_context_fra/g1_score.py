#!/usr/bin/env python3
"""G1 FRA scoring (PLAN.md section 5). Run ONCE, on the final 28-day FRA data, after the frozen files are committed.

  python3 g1_score.py --actual <fra-public-game.json | csv with name,gih[,gih_n]> [--min-games 500] [--arms arm1,arm2,arm12]
  python3 g1_score.py --selftest        # synthetic actuals made from the frozen predictions themselves; checks the code path only

Reads the frozen prediction files (sha256 verified), never refits anything. The actual file is read only here.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'c9_power_questions' / 'fra_frozen_predictions.csv'
BOOT, SEED = 10000, 20261028


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


def verify(arm):
    meta = json.loads((HERE / f'fra_frozen_{arm}.json').read_text())
    got = hashlib.sha256((HERE / f'fra_frozen_{arm}.csv').read_bytes()).hexdigest()
    assert got == meta['sha256'], f'{arm}: frozen file changed after freezing'
    return pd.read_csv(HERE / f'fra_frozen_{arm}.csv')


def metrics(df, col):
    d = df[col] - df['actual']
    rank = df['actual'].rank(ascending=False, method='first')
    return {'mae': float(d.abs().mean() * 100), 'spearman': float(spearmanr(df[col], df['actual']).correlation),
            'under_top10': float(-d[rank <= 10].mean() * 100), 'under_top20': float(-d[rank <= 20].mean() * 100)}


def boot(df, c0, c1, ref_mask, rng):
    n = len(df)
    out = {k: [] for k in ('dmae', 'dspear', 'dtop10', 'dtop20', 'dmae_ref')}
    for _ in range(BOOT):
        i = rng.integers(0, n, n)
        s = df.iloc[i]
        a, b = metrics(s, c0), metrics(s, c1)
        out['dmae'].append(b['mae'] - a['mae']); out['dspear'].append(b['spearman'] - a['spearman'])
        out['dtop10'].append(b['under_top10'] - a['under_top10']); out['dtop20'].append(b['under_top20'] - a['under_top20'])
        sr = s[ref_mask.iloc[i].to_numpy()]
        out['dmae_ref'].append(float(((sr[c1] - sr['actual']).abs().mean() - (sr[c0] - sr['actual']).abs().mean()) * 100) if len(sr) else np.nan)
    return {k: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))] for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--actual'); ap.add_argument('--min-games', type=int, default=500)
    ap.add_argument('--arms', default='arm1,arm2,arm12'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    base = pd.read_csv(BASE)
    arms = [x for x in a.arms.split(',') if (HERE / f'fra_frozen_{x}.csv').exists()]
    frames = {x: verify(x) for x in arms}
    if a.selftest:
        rng = np.random.default_rng(1)
        act = base[['name']].assign(gih=(base['pred_B10'] + rng.normal(0, 0.03, len(base))) * 100)
        act.to_csv(HERE / '_selftest_actual.csv', index=False); a.actual = str(HERE / '_selftest_actual.csv')
    act = load_actual(a.actual, a.min_games)
    df = base[['id', 'name', 'pred_B10']].rename(columns={'pred_B10': 'arm0'})
    for x, f in frames.items():
        df = df.merge(f[['id', f'pred_{x}']].rename(columns={f'pred_{x}': x}), on='id')
    unmatched = sorted(set(act['name']) - set(df['name']))
    df = df.merge(act, on='name')
    print(f'scored cards {len(df)}, unmatched actual names {len(unmatched)} {unmatched[:5]}')
    jc = pd.read_csv(HERE / 'judge_cards.csv'); ref_ids = set(jc.loc[jc.is_anchor == 0, 'id'])
    sc = pd.read_csv(HERE / 'sc_features.csv.gz'); sc = sc[sc.key.str.startswith('FRA|')]
    df['ref1'] = df['id'].isin(ref_ids)
    df['ref2'] = df['id'].map(lambda i: sc.loc[sc.key == f'FRA|{i}', 'sc_n_sup'].iloc[0] > 0)
    rng = np.random.default_rng(SEED)
    res = {'n': len(df), 'arm0': metrics(df, 'arm0')}
    for x in frames:
        m = metrics(df, x)
        mask = df['ref1'] if x != 'arm2' else df['ref2']
        ci = boot(df, 'arm0', x, mask, rng)
        d = {k: m[k] - res['arm0'][k] for k in m}
        ref = df[mask]
        d_ref = float(((ref[x] - ref['actual']).abs().mean() - (ref['arm0'] - ref['actual']).abs().mean()) * 100)
        mv = (df[x] - df['arm0']).abs() > 0.001
        better = int((((df[x] - df['actual']).abs() < (df['arm0'] - df['actual']).abs()) & mv).sum())
        crit = {'mae_not_worse': d['mae'] <= 0, 'spearman_not_worse': d['spearman'] >= 0,
                'top20_under_shrinks_and_top10_not_larger': d['under_top20'] < 0 and d['under_top10'] <= 0}
        crit['pass'] = all(crit.values())
        res[x] = {**m, 'delta': d, 'ci95': ci, 'ref_cards': int(mask.sum()), 'delta_mae_ref_cards': d_ref, 'moved_cards': int(mv.sum()),
                  'moved_and_closer': better, 'criteria': crit}
    out = HERE / ('selftest_result.json' if a.selftest else 'fra_score.json')
    json.dump(res, open(out, 'w'), indent=1)
    df.to_csv(HERE / ('_selftest_cards.csv' if a.selftest else 'fra_score_cards.csv'), index=False)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
