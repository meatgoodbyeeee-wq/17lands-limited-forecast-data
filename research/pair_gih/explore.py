"""Colour-pair card GIH, exploratory step 1 (not pre-registered; decides nothing).

Questions
 E1  Within a set, how much of the spread of cell GIH (card x pair, >= MIN games) is card, pair, and card x pair
     interaction, after removing binomial noise?
 E2  Error of simple forecasts of cell GIH (MAE in pp, cells with a B11g prediction):
     honest   H0 pred for every pair; H1 pred + lam*(pair WR - set mean), pair WR known (oracle), lam leave-one-set-out
     oracle   O0 actual overall GIH for every pair; O1 O0 + lam*pair dev; O2 in-sample additive fit (card + pair)
     noise floor: sqrt(2/pi)*SE, the MAE left even if every cell's true value were known
 E3  Where the interaction lives: residual of the additive fit by how the card's colours relate to the pair.

     realistic  H1p/H2p: as H1/H2 but the pair strength is the D9 leave-one-set-out forecast D_B5 (best pre-release pair
               forecast so far, a reported arm in D9; built on B5 card predictions), not the actual pair WR

Usage: python3 research/pair_gih/explore.py <cells.csv.gz> <out.json> <d9 pair_table.csv>
"""
import json, sys
import numpy as np, pandas as pd

MIN = 500


def additive(g, iters=50):
    """Weighted two-way additive fit y = m + a_card + b_pair (weights = games)."""
    y, w = g['y'].values, g['games'].values.astype(float)
    ci, pi = g['name'].factorize()[0], g['pair'].factorize()[0]
    m = np.average(y, weights=w)
    a, b = np.zeros(ci.max() + 1), np.zeros(pi.max() + 1)
    for _ in range(iters):
        r = y - m - b[pi]
        a = np.bincount(ci, w * r) / np.bincount(ci, w)
        r = y - m - a[ci]
        b = np.bincount(pi, w * r) / np.bincount(pi, w)
        b -= np.average(b[pi], weights=w)
    return m + a[ci] + b[pi], m + a[ci], b[pi]


def relation(colors, pair):
    if not isinstance(colors, str) or colors == '':
        return 'colourless'
    inside = sum(c in pair for c in colors)
    if len(colors) == 1:
        return 'mono_on' if inside else 'mono_off(splash)'
    if len(colors) == 2:
        return 'gold_exact' if inside == 2 else ('gold_half' if inside == 1 else 'gold_off')
    return '3plus_' + ('all' if inside == len(colors) else str(inside))


def main(cells, out, d9):
    d = pd.read_csv(cells, keep_default_na=False, na_values=[''])
    d = d[d['games'] >= MIN].copy()
    d['y'] = 100 * d['gih_pair']
    d['se'] = 100 * np.sqrt(d['gih_pair'] * (1 - d['gih_pair']) / d['games'])
    d['pair_dev'] = 100 * (d['pair_wr'] - d['set_pair_wr'])
    d['all'] = 100 * d['gih_all']
    d['pred100'] = 100 * d['pred']
    d['rel'] = [relation(c, p) for c, p in zip(d['colors'], d['pair'])]
    pt = pd.read_csv(d9)[['set', 'pair', 'D_B5']]
    d = d.merge(pt, on=['set', 'pair'], how='left')
    res = {'min_games': MIN, 'cells': int(len(d)), 'sets': int(d['set'].nunique()), 'cards': int(d[['set', 'name']].drop_duplicates().shape[0])}

    # E1 decomposition per set
    e1 = []
    parts = []
    for s, g in d.groupby('set'):
        g = g.copy()
        g['fit'], g['card_part'], g['pair_part'] = additive(g)
        g['resid'] = g['y'] - g['fit']
        n, C, P = len(g), g['name'].nunique(), g['pair'].nunique()
        noise = (g['se'] ** 2).mean()
        resid_noise = noise * (n - C - P + 1) / n
        e1.append({'set': s, 'cells': n, 'cards': C, 'cells_per_card': n / C,
                   'var_total': g['y'].var(), 'var_noise': noise,
                   'var_card': g['card_part'].var(), 'var_pair': g['pair_part'].var(),
                   'var_resid': g['resid'].var(), 'var_interaction_true': g['resid'].var() - resid_noise})
        parts.append(g)
    e1 = pd.DataFrame(e1)
    d = pd.concat(parts)
    res['E1_mean_over_sets'] = e1.drop(columns='set').mean().round(3).to_dict()
    res['E1_sd_pp'] = {k: round(float(np.sqrt(max(e1[k].mean(), 0))), 3) for k in
                       ['var_total', 'var_noise', 'var_card', 'var_pair', 'var_interaction_true']}
    res['E1_per_set'] = e1.round(3).to_dict('records')

    # E2 forecasts on cells with a prediction
    h = d[d['pred'].notna()].copy()
    sets = sorted(h['set'].unique())

    def lam_loso(x, base):  # OLS slope of (y - base) on x, fitted on the other sets
        out = pd.Series(index=h.index, dtype=float)
        lams = []
        for s in sets:
            tr, te = h['set'] != s, h['set'] == s
            r, xx = (h.loc[tr, 'y'] - h.loc[tr, base]), h.loc[tr, x]
            lam = float((xx * r).sum() / (xx * xx).sum())
            lams.append(lam)
            out[te] = h.loc[te, base] + lam * h.loc[te, x]
        return out, float(np.mean(lams))

    h['H0'] = h['pred100']
    h['H1'], lam_h = lam_loso('pair_dev', 'pred100')
    h['O0'] = h['all']
    h['O1'], lam_o = lam_loso('pair_dev', 'all')
    h['O2'] = h['fit']
    h['H1p'], lam_p = lam_loso('D_B5', 'pred100')
    # H2: H1 + an offset per colour relation of card and pair (offsets fitted on the other sets)
    h['rel'] = [relation(c, p) for c, p in zip(h['colors'].fillna(''), h['pair'])]
    h['H2'] = h['H2p'] = h['H0r'] = np.nan
    for s in sets:
        tr, te = h['set'] != s, h['set'] == s
        off = (h.loc[tr, 'y'] - h.loc[tr, 'H1']).groupby(h.loc[tr, 'rel']).mean()
        h.loc[te, 'H2'] = h.loc[te, 'H1'] + h.loc[te, 'rel'].map(off).fillna(0)
        offp = (h.loc[tr, 'y'] - h.loc[tr, 'H1p']).groupby(h.loc[tr, 'rel']).mean()
        h.loc[te, 'H2p'] = h.loc[te, 'H1p'] + h.loc[te, 'rel'].map(offp).fillna(0)
        off0 = (h.loc[tr, 'y'] - h.loc[tr, 'H0']).groupby(h.loc[tr, 'rel']).mean()
        h.loc[te, 'H0r'] = h.loc[te, 'H0'] + h.loc[te, 'rel'].map(off0).fillna(0)
    floor = float((np.sqrt(2 / np.pi) * h['se']).mean())

    def mae(col, g=h):
        return float((g['y'] - g[col]).abs().mean())

    res['E2'] = {'cells': int(len(h)), 'noise_floor_mae': round(floor, 3), 'lambda_H1': round(lam_h, 3), 'lambda_O1': round(lam_o, 3), 'lambda_H1p': round(lam_p, 3),
                 'mae': {k: round(mae(k), 3) for k in ['H0', 'H0r', 'H1p', 'H2p', 'H1', 'H2', 'O0', 'O1', 'O2']},
                 'mae_H2_by_relation': {k: round(float((g['y'] - g['H2']).abs().mean()), 3) for k, g in h.groupby('rel')},
                 'mae_H1_by_relation': {k: round(float((g['y'] - g['H1']).abs().mean()), 3) for k, g in h.groupby('rel')},
                 'sets_H2p_better_than_H0': int(sum((g['y'] - g['H2p']).abs().mean() < (g['y'] - g['H0']).abs().mean() for _, g in h.groupby('set'))),
                 'sets_H0r_better_than_H0': int(sum((g['y'] - g['H0r']).abs().mean() < (g['y'] - g['H0']).abs().mean() for _, g in h.groupby('set'))),
                 'sets_H2_better_than_H1': int(sum((g['y'] - g['H2']).abs().mean() < (g['y'] - g['H1']).abs().mean() for _, g in h.groupby('set'))),
                 'mae_card_overall_H0_vs_actual_overall': round(float((h.drop_duplicates(['set', 'name'])['pred100'] - h.drop_duplicates(['set', 'name'])['all']).abs().mean()), 3),
                 'mean_within_set_spearman': {k: round(float(h.groupby('set').apply(lambda g: g['y'].corr(g[k], method='spearman')).mean()), 3) for k in ['H0', 'H0r', 'H1p', 'H2p', 'H1', 'H2', 'O0', 'O1', 'O2']}}
    # within-card spread: how far apart a card's pairs are, and how much of that pair spread H1/O1 capture
    w = h.groupby(['set', 'name']).filter(lambda g: len(g) >= 3)
    wc = w.assign(yc=w['y'] - w.groupby(['set', 'name'])['y'].transform('mean'),
                  pc=w['pair_dev'] - w.groupby(['set', 'name'])['pair_dev'].transform('mean'))
    res['E2_within_card'] = {'cards_with_3plus_pairs': int(w[['set', 'name']].drop_duplicates().shape[0]),
                             'sd_within_card_pp': round(float(wc['yc'].std()), 3),
                             'noise_sd_pp': round(float(np.sqrt((wc['se'] ** 2).mean())), 3),
                             'corr_within_card_with_pair_dev': round(float(wc['yc'].corr(wc['pc'])), 3),
                             'slope_within_card_on_pair_dev': round(float((wc['yc'] * wc['pc']).sum() / (wc['pc'] ** 2).sum()), 3)}

    # E3 residual of the additive fit by colour relation (all cells with colours)
    r = d[d['pred'].notna()].copy()  # cards in the B11g pool; colourless cards have empty colours
    r['rel'] = [relation(c, p) for c, p in zip(r['colors'].fillna(''), r['pair'])]
    r = r.join(h[['H1']])
    t = r.groupby('rel').agg(cells=('y', 'size'), mean_resid=('resid', 'mean'), sd_resid=('resid', 'std'),
                             mean_resid_H1=('H1', lambda s: float((r.loc[s.index, 'y'] - s).mean())),
                             noise_sd=('se', lambda s: float(np.sqrt((s ** 2).mean()))), mean_games=('games', 'mean'))
    t['sets_positive'] = r.groupby(['rel', 'set'])['resid'].mean().gt(0).groupby('rel').sum()
    t['sets_present'] = r.groupby(['rel', 'set']).size().groupby('rel').size()
    res['E3_by_relation'] = t.round(3).reset_index().to_dict('records')
    # residual vs pair_dev slope by relation (does a strong pair lift its own-colour cards more than splashes?)
    res['E3_slope_resid_on_pair_dev'] = {k: round(float((g['resid'] * g['pair_dev']).sum() / (g['pair_dev'] ** 2).sum()), 3)
                                          for k, g in r.groupby('rel') if len(g) > 100}
    json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False)
    h.to_csv(out.replace('.json', '_cells.csv.gz'), index=False)
    print(json.dumps({k: v for k, v in res.items() if k != 'E1_per_set'}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main(*sys.argv[1:4])
