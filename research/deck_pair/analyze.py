"""Deck colour step 1 measurements M1-M3 (see PLAN.md).

  python3 research/deck_pair/analyze.py
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / 'data'
sys.path.insert(0, str(ROOT / 'research/production_c3'))
PAIRS = ["WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG"]
COLS = "WUBRG"


def load_cards():
    import export_gih_c3_28set as e
    pool, _, _ = e.training()
    oof = pd.read_csv(ROOT / 'research/production_c3/oof_28set.csv.gz')
    d = oof.merge(pool[['set', 'name', 'type_land'] + [f'color_{c}' for c in COLS]], on=['set', 'name'], validate='one_to_one')
    d['colors'] = d.apply(lambda r: ''.join(c for c in COLS if r[f'color_{c}'] == 1), axis=1)
    return d


def pair_table(sets):
    rows = []
    for s in sets:
        p = pd.read_csv(DATA / f'{s}_pairs.csv', keep_default_na=False)
        u = p[(~p['splash'].astype(str).str.lower().eq('true')) & p['main_colors'].isin(PAIRS)]
        for pair in PAIRS:
            q = u[u['main_colors'] == pair]
            g, w = q['games'].sum(), q['wins'].sum()
            h = {hf: q[q['half'] == hf] for hf in (0, 1)}
            rows.append({'set': s, 'pair': pair, 'games': g, 'wr': w / g * 100,
                         'wr_h0': h[0]['wins'].sum() / max(h[0]['games'].sum(), 1) * 100,
                         'wr_h1': h[1]['wins'].sum() / max(h[1]['games'].sum(), 1) * 100})
    t = pd.DataFrame(rows)
    t['wr_c'] = t['wr'] - t.groupby('set')['wr'].transform('mean')
    return t


def mean_rho(t, a, b):
    return float(np.mean([spearmanr(g[a], g[b]).correlation for _, g in t.groupby('set')]))


def fits(colors, pair):
    return len(colors) > 0 and all(c in pair for c in colors)


def main():
    cards = load_cards()
    sets = sorted(cards['set'].unique())
    missing = [s for s in sets if not (DATA / f'{s}_pairs.csv').exists()]
    assert not missing, missing
    pt = pair_table(sets)
    res = {'sets': len(sets)}

    # M1
    se = np.sqrt(0.25 / pt['games']) * 100
    sd = pt.groupby('set')['wr'].std()
    res['M1'] = {'pair_wr_within_set_sd_mean': float(sd.mean()), 'pair_wr_sampling_se_median': float(se.median()),
                 'split_half_spearman_mean': mean_rho(pt, 'wr_h0', 'wr_h1'),
                 'per_set_sd': sd.round(3).to_dict()}

    # M2: current formula
    cu = cards[cards['rarity_ord'] <= 1]
    rows = []
    for s, g in cu.groupby('set'):
        for pair in PAIRS:
            e = g[g['colors'].apply(lambda c: fits(c, pair))]
            rows.append({'set': s, 'pair': pair, 'f_pred': e['pred'].mean(), 'f_act': e['actual_gih'].mean(), 'n': len(e)})
    f = pd.DataFrame(rows).merge(pt, on=['set', 'pair'])
    res['M2'] = {'formula_pred_spearman': mean_rho(f, 'f_pred', 'wr'), 'formula_actual_cards_spearman': mean_rho(f, 'f_act', 'wr'),
                 'per_set': {s: {'pred': float(spearmanr(g['f_pred'], g['wr']).correlation),
                                 'act': float(spearmanr(g['f_act'], g['wr']).correlation)} for s, g in f.groupby('set')}}

    # M3: card GIH ceiling with known pair WRs
    cp = pd.concat([pd.read_csv(DATA / f'{s}_cardpair.csv.gz') for s in sets])
    cp = cp.rename(columns={'card_name': 'name'})
    d = cards.merge(cp, on=['set', 'name'], how='left')
    wrc = pt.pivot(index='set', columns='pair', values='wr_c')[PAIRS]
    WR = wrc.loc[d['set']].values / 100
    sh_a = d[[f'{p}_games' for p in PAIRS]].fillna(0).values.astype(float)
    sh_a = sh_a / np.maximum(sh_a.sum(1, keepdims=True), 1)
    def share_b(c):
        if not c:
            return [1.0] * len(PAIRS)
        w = [1.0 if fits(c, p) else 0.0 for p in PAIRS]
        if sum(w) == 0:  # three or more colours: the pairs inside the card's colours
            w = [1.0 if all(x in c for x in p) else 0.0 for p in PAIRS]
        return w
    sh_b = np.array([share_b(c) for c in d['colors']])
    sh_b = sh_b / sh_b.sum(1, keepdims=True)
    d['b_A'] = (sh_a * WR).sum(1)
    d['b_B'] = (sh_b * WR).sum(1)
    d['res'] = d['actual_gih'] - d['pred']

    def evaluate(adj):
        mae = float(np.mean(np.abs(adj - d['actual_gih'])) * 100)
        rho = float(np.mean([spearmanr(adj[idx], d.loc[idx, 'actual_gih']).correlation for _, idx in d.groupby('set').groups.items()]))
        return {'mae_pp': mae, 'spearman_mean': rho}
    out = {'pred': evaluate(d['pred'].values)}
    for k in ['b_A', 'b_B']:
        adj = d['pred'].values.copy()
        lams = []
        for s in sets:
            tr, te = d['set'] != s, d['set'] == s
            x, y = d.loc[tr, k].values, d.loc[tr, 'res'].values
            lam = float((x @ y) / (x @ x))
            lams.append(lam)
            adj[te.values] = d.loc[te, 'pred'].values + lam * d.loc[te, k].values
        out[k] = {**evaluate(adj), 'lambda_mean': float(np.mean(lams))}
    res['M3'] = out
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    pt.round(3).to_csv(HERE / 'pair_wr.csv', index=False)
    f.round(4).to_csv(HERE / 'formula_backtest.csv', index=False)
    print(json.dumps({k: (v if k != 'M2' else {kk: vv for kk, vv in v.items() if kk != 'per_set'}) for k, v in res.items()
                      if k != 'M1'} | {'M1': {k: v for k, v in res['M1'].items() if k != 'per_set'}}, indent=1))


if __name__ == '__main__':
    main()
