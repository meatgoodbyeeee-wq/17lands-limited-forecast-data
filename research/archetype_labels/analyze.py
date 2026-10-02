"""Improvement 4 (redo): official-archetype labels -> pair strength, Rule A (see PLAN.md)."""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/deck_model'))
import deck_model as dm  # noqa: E402

AF = ['A1', 'A2', 'A3', 'A4', 'A5']
ORDER = 'WUBRG'


def norm(c):
    c = str(c).strip()
    return '' if c in ('', 'none') else ''.join(x for x in ORDER if x in c)


def labels():
    out = []
    for f in sorted(glob.glob(str(HERE / 'raw/*.csv'))):
        s = Path(f).stem
        r = pd.read_csv(f, keep_default_na=False)
        i = pd.read_csv(HERE / f'input/{s}.csv', keep_default_na=False)[['id', 'name']]
        r = r.merge(i, on='id', validate='one_to_one')
        r['set'] = s
        r['prim'] = r['primary'].map(norm)
        r['sec'] = r['secondary'].map(lambda x: [norm(c) for c in str(x).split('+') if norm(c)])
        out.append(r[['set', 'name', 'prim', 'sec', 'role']])
    return pd.concat(out, ignore_index=True)


def pair_in(code, pair):
    return code != '' and all(c in pair for c in code) if len(code) <= 2 else all(c in code for c in pair)


def afeatures(d):
    rows = []
    for s, g in d.groupby('set'):
        smean = g['pred'].mean()
        g = g[(g['type_land'] != 1)]
        for pair in dm.PAIRS:
            m = g['prim'].apply(lambda c: c != '' and (c == pair or (len(c) == 3 and all(x in c for x in pair))))
            prim = g[m]
            pe = prim[prim['role'].isin(['P', 'E'])]
            wsum = g['w'].sum()
            wp, we = prim.loc[prim['role'] == 'P', 'w'].sum(), prim.loc[prim['role'] == 'E', 'w'].sum()
            anyl = g.apply(lambda r: (r['prim'] == pair) or (pair in r['sec']), axis=1)
            cu = g[anyl & (g['rarity_ord'] <= 1)]
            pay = prim[prim['role'] == 'P']
            rows.append({'set': s, 'pair': pair, 'A1': pe['w'].sum() / wsum,
                         'A2': pe['pred'].mean() if len(pe) else smean,
                         'A3': min(wp, we) / wsum, 'A4': float(len(cu)),
                         'A5': pay['pred'].mean() if len(pay) else smean})
    a = pd.DataFrame(rows)
    for k in AF:
        a[k] = a[k] - a.groupby('set')[k].transform('mean')
    return a


def main():
    d = dm.load_cards()
    d = d[d['set'].isin(pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')['set'].unique())].merge(labels(), on=['set', 'name'], how='left')
    assert d['prim'].notna().mean() > 0.995, d['prim'].isna().mean()
    d['prim'] = d['prim'].fillna(''); d['role'] = d['role'].fillna('G')
    d['sec'] = d['sec'].apply(lambda x: x if isinstance(x, list) else [])
    d = d.drop_duplicates(['set', 'name'])
    none_share = d.groupby('set')['prim'].apply(lambda x: float((x == '').mean())).round(3).to_dict()
    pw = pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')[['set', 'pair', 'wr_c']].rename(columns={'wr_c': 'y'})
    t = dm.features(d).merge(afeatures(d), on=['set', 'pair']).merge(pw, on=['set', 'pair']).reset_index(drop=True)
    assert t['set'].nunique() == 26 and len(t) == 260
    t['D'] = dm.loso_ridge(t, dm.FEATS, dm.ALPHA)
    t['A'] = dm.loso_ridge(t, dm.FEATS + AF, dm.ALPHA)
    t['Aonly'] = dm.loso_ridge(t, AF, dm.ALPHA)
    t['F0s'] = dm.loso_scale(t, 'F0')
    for a in dm.ALPHA_SENS:
        t[f'A_a{a}'] = dm.loso_ridge(t, dm.FEATS + AF, a)
    rho = {k: dm.per_set_rho(t, k) for k in ['F0', 'D', 'A', 'Aonly']}
    m = lambda k: float(np.mean(list(rho[k].values())))
    res = {'none_share_by_set': none_share,
           'F0': {'spearman_mean': m('F0'), 'mae_pp': float((t['F0s'] - t['y']).abs().mean())},
           'D': {'spearman_mean': m('D'), 'mae_pp': float((t['D'] - t['y']).abs().mean())},
           'A': {'spearman_mean': m('A'), 'mae_pp': float((t['A'] - t['y']).abs().mean()),
                 'sets_better_than_F0': int(sum(rho['A'][s] > rho['F0'][s] for s in rho['A']))},
           'Aonly': {'spearman_mean': m('Aonly'), 'mae_pp': float((t['Aonly'] - t['y']).abs().mean())},
           'sensitivity': {c: {'spearman_mean': float(np.mean(list(dm.per_set_rho(t, c).values()))), 'mae_pp': float((t[c] - t['y']).abs().mean())}
                           for c in [f'A_a{a}' for a in dm.ALPHA_SENS]},
           'single_feature_spearman': {k: float(np.mean(list(dm.per_set_rho(t, k).values()))) for k in AF}}
    res['rule_a'] = {'spearman': res['A']['spearman_mean'] >= res['F0']['spearman_mean'] + .05 and res['A']['spearman_mean'] >= res['D']['spearman_mean'],
                     'sets': res['A']['sets_better_than_F0'] >= 15, 'mae': res['A']['mae_pp'] < res['F0']['mae_pp']}
    res['rule_a']['pass'] = all(res['rule_a'].values())
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    t.round(4).to_csv(HERE / 'pair_features.csv', index=False)
    print(json.dumps({k: v for k, v in res.items() if k != 'none_share_by_set'}, indent=1))


if __name__ == '__main__':
    main()
