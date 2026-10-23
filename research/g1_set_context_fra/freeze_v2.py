#!/usr/bin/env python3
"""G1 v2: freeze the FRA predictions (PLAN_v2.md 8 and 13: post-hoc R/M-only arm). Run after raw_v2/*/FRA_*.txt are judged and checked,
before any FRA outcome is read.

  python3 freeze_v2.py --fra <limited-forecast-pages>/data/target.json.gz

Writes fra_frozen_v2.csv and fra_frozen_v2.json (sha256). Reads only the card list ('cards') of the target file.
  pred_arm0     frozen B10 (research/c9_power_questions/fra_frozen_predictions.csv, pred_B10); a re-run in this environment must match it
  pred_v2       new C9 (3-pass v2, converted to the old scale, 7.2) on FRA R/M cards only; C/U and lands keep the old C9   <- the arm scored with F1-F3
  pred_v2_raw   same, without the conversion (report)
  pred_v2_all   converted new C9 on all judged FRA cards (report only)
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g1  # noqa: E402  (B10 definition, FRA frame; unchanged)
import g1v2  # noqa: E402
c9, e = g1.c9, g1.e
F, MAX = c9.F, [4, 4, 4, 4, 3, 4, 10]
BASE = HERE.parent / 'c9_power_questions' / 'fra_frozen_predictions.csv'


def v2_answers():
    """{unit n: 3x7 array} for the FRA units, from raw_v2 (all three passes must be complete)."""
    B = pd.read_csv(HERE / 'batches.csv')
    raws = {}
    for p in g1v2.PASSES:
        for b in B[(B['pass'] == p) & (B['set'] == 'FRA')].batch:
            r, err = g1v2.load_raw(p, b)
            assert not err, err
            raws.setdefault(p, {}).update(r)
    U = pd.read_csv(HERE / 'units.csv')
    U = U[U.set == 'FRA']
    out = {int(n): np.array([raws[p][int(n)] for p in g1v2.PASSES], float) for n in U.n}
    return out, dict(zip(U.n.astype(int), U.key))


def setinfo_units():
    s = set()
    for f in sorted((HERE / 'input_v2' / 'p1').glob('FRA_*.txt')):
        for blk in re.split(r'\n(?=#\d+ \|)', f.read_text()):
            m = re.match(r'#(\d+) \|', blk.strip())
            if m and 'SET INFO:' in blk:
                s.add(int(m.group(1)))
    return s


def c9_cols(m, sd):
    d = dict(zip(c9.MEAN, m)); d.update(zip(c9.SD, sd))
    d['c9_impuna'] = m[0] + m[1]; d['c9_valfloor'] = m[2] + m[3]; d['c9_bomb'] = m[6] - 1.25 * m[5]
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--fra', type=Path, required=True); a = ap.parse_args()
    conv = json.loads((HERE / 'eval_v2' / 'conversion_all28.json').read_text())
    al, be = np.array([conv[q]['alpha'] for q in F]), np.array([conv[q]['beta'] for q in F])
    pool, base, cols, nums10, _ = g1.load_pool()
    fra, f, keys = g1.fra_frame(a.fra, pool, base, cols)
    rarity = {f"FRA|{c['id']}": c['rarity'] for c in fra}
    ans, n2key = v2_answers()
    si = setinfo_units()
    key2n = {k: n for n, k in n2key.items()}
    _, _, _, p0 = e.predict(pool, f, nums10)
    variants = {'rm_conv': f.copy(), 'rm_raw': f.copy(), 'all_conv': f.copy()}
    rows = []
    for i, k in enumerate(keys):
        r = {'id': fra[i]['id'], 'name': fra[i]['name'], 'rarity': rarity[k], 'is_rm': int(rarity[k] in ('rare', 'mythic')),
             'judged': int(k in key2n), 'has_setinfo': int(key2n.get(k) in si)}
        old = f.loc[i, c9.MEAN].to_numpy(float)
        r.update({f'old_{q}': x for q, x in zip(F, old)})
        if k in key2n:
            v = ans[key2n[k]]
            m, sd = v.mean(0), v.std(0)
            mc = np.clip(al + be * m, 0, MAX)
            for name, mm, ss, use in (('rm_conv', mc, be * sd, r['is_rm']), ('rm_raw', m, sd, r['is_rm']), ('all_conv', mc, be * sd, 1)):
                if use:
                    for c, x in c9_cols(mm, ss).items():
                        variants[name].loc[i, c] = x
            r.update({f'new_conv_{q}': x for q, x in zip(F, mc)}); r.update({f'new_raw_{q}': x for q, x in zip(F, m)})
        rows.append(r)
    out = pd.DataFrame(rows)
    b = pd.read_csv(BASE).set_index('id')
    out['pred_arm0'] = out['id'].map(b['pred_B10'])
    out['pred_B10_rerun'] = p0
    drift = float(np.abs(out.pred_B10_rerun - out.pred_arm0).max() * 100)
    assert drift < 1e-6, f'B10 re-run differs from the frozen B10 by {drift} pp'
    for col, name in (('pred_v2', 'rm_conv'), ('pred_v2_raw', 'rm_raw'), ('pred_v2_all', 'all_conv')):
        _, _, _, p = e.predict(pool, variants[name], nums10)
        out[col] = p
    out['new_GRADE_conv'] = out['new_conv_GRADE'].fillna(out['old_GRADE'])
    out['new_GRADE_raw'] = out['new_raw_GRADE'].fillna(out['old_GRADE'])
    # P4/grade moves on FRA concern the arm that is scored: only R/M cards change
    out.loc[out.is_rm == 0, 'new_GRADE_conv'] = out.loc[out.is_rm == 0, 'old_GRADE']
    out.loc[out.is_rm == 0, 'new_GRADE_raw'] = out.loc[out.is_rm == 0, 'old_GRADE']
    cu = out.is_rm == 0
    out.to_csv(HERE / 'fra_frozen_v2.csv', index=False)
    meta = {'plan': 'PLAN_v2 sections 8 and 13 (post-hoc R/M-only arm)', 'n': len(out), 'n_rm': int(out.is_rm.sum()), 'n_judged': int(out.judged.sum()),
            'b10_rerun_max_abs_diff_pp': drift,
            'cu_pred_v2_max_abs_diff_vs_arm0_pp': float(np.abs(out.loc[cu, 'pred_v2'] - out.loc[cu, 'pred_arm0']).max() * 100),
            'mean_abs_change_pp': {c: float(np.abs(out[c] - out.pred_arm0).mean() * 100) for c in ('pred_v2', 'pred_v2_raw', 'pred_v2_all')},
            'mean_grade_move_rm_conv': float((out.new_GRADE_conv - out.old_GRADE)[out.is_rm == 1].mean()),
            'sha256': hashlib.sha256((HERE / 'fra_frozen_v2.csv').read_bytes()).hexdigest()}
    (HERE / 'fra_frozen_v2.json').write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == '__main__':
    main()
