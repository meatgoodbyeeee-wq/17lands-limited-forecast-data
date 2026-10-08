"""D9: colour-pair strength (Rule P9) and its feedback into card GIH (Rule F9), see PLAN.md.

  python3 research/d9_colour_strength/d9.py
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/deck_model'))
sys.path.insert(0, str(ROOT / 'research/c8_set_environment'))
import deck_model as dm  # noqa: E402
import env as c8env  # noqa: E402

PAIRS, FEATS = dm.PAIRS, dm.FEATS
P9F = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']
NA = -1.0


def b5():
    o = pd.read_csv(ROOT / 'research/c5_atomic_effects/oof_B5.csv.gz')
    return o


def d_b5_features():
    cards = dm.load_cards()
    o = b5()[['set', 'name', 'pred']].rename(columns={'pred': 'pred_b5'})
    cards = cards.merge(o, on=['set', 'name'], how='left', validate='one_to_one')
    assert cards['pred_b5'].notna().mean() > .99
    cards['pred'] = cards['pred_b5'].fillna(cards['pred'])
    f = dm.features(cards)
    return f.rename(columns={'F0': 'F0_B5'})


def objective_features():
    t = c8env.table()
    g = pd.read_csv(ROOT / 'research/c8_set_environment/c8_features.csv.gz')
    t = t.merge(g, on='key', how='left')
    t = t[~t['type_line'].str.contains('Land') & (t['colors'] != '') & (t['set'] != 'FRA')]
    val = lambda c: np.where(t[c].isna() | (t[c] == NA), 0.0, t[c])
    t['is_rm'] = t['n_removal'] > 0
    t['is_cr'] = t['is_creature'] == 1
    t['v_reach'] = val('c8_reach_share') * t['is_rm']
    t['v_threat'] = val('c8_reach_threat_share') * t['is_rm']
    t['v_body'] = (t['is_cr'] & t['mv'].between(2, 3) & (val('c8_stat_rank_mv') >= .5)).astype(float)
    t['v_evasive'] = (t['is_cr'] & (val('c8_blockable_share') < .9) & (t['c8_blockable_share'] != NA)).astype(float)
    t['v_combat'] = (val('c8_atk_survive') + val('c8_blk_survive')) / 2 * t['is_cr']
    t['v_value'] = ((t['draw_n'] > 0) | (t['token_n'] > 0) | (t['is_cr'] & (t['etb'] > 0))).astype(float)
    t['v_aggro'] = np.where(t['is_cr'] & (t['mv'] <= 3), pd.to_numeric(t['power'], errors='coerce').fillna(0), 0.0)
    rows = []
    for s, gs in t.groupby('set'):
        for pair in PAIRS:
            e = gs[gs['colors'].apply(lambda c: dm.fits(c, pair))]
            w = e['w']
            rows.append({'set': s, 'pair': pair, 'P1': (w * e['v_reach']).sum(), 'P2': (w * e['v_threat']).sum(),
                         'P3': (w * e['v_body']).sum(), 'P4': (w * e['v_evasive']).sum(), 'P5': (w * e['v_combat']).sum(),
                         'P6': (w * e['v_value']).sum(), 'P7': (w * e['v_aggro']).sum()})
    f = pd.DataFrame(rows)
    for k in P9F:
        f[k] = f[k] - f.groupby('set')[k].transform('mean')
    return f


def rho(t, col):
    return dm.per_set_rho(t, col)


def card_stage(t, cols):
    o = b5()
    o = o[o['set'].isin(t['set'].unique())].copy()
    u = pd.read_csv(ROOT / 'research/c5_atomic_effects/cards.csv.gz', keep_default_na=False)
    colmap = {k: r.colors for r in u.itertuples() for k in r.keys.split(';')}
    o['col'] = (o['set'] + '|' + o['name']).map(colmap).fillna('')
    o['res'] = o['actual_gih'] - o['pred']
    out, res = {}, {}
    for c in cols:
        look = {(r.set, r.pair): getattr(r, c) for r in t.itertuples()}

        def cs(s, col):
            if len(col) == 1:
                return np.mean([look[(s, p)] for p in PAIRS if col in p])
            if len(col) == 2:
                p = [p for p in PAIRS if set(p) == set(col)]
                return look[(s, p[0])] if p else 0.0
            return 0.0
        o[f'cs_{c}'] = [cs(s, col) for s, col in zip(o['set'], o['col'])]
        adj = np.full(len(o), np.nan)
        for s in o['set'].unique():
            tr, te = (o['set'] != s).to_numpy(), (o['set'] == s).to_numpy()
            x, y = o.loc[tr, f'cs_{c}'].to_numpy(), o.loc[tr, 'res'].to_numpy()
            b = float(x @ y / (x @ x)) if (x @ x) else 0.0
            adj[te] = o.loc[te, 'pred'].to_numpy() + b * o.loc[te, f'cs_{c}'].to_numpy()
        o[f'B9_{c}'] = adj
    m0 = c8env.c5.metrics(o.assign(pred=o['pred']))
    res['B5'] = m0[0]
    per0 = m0[1]
    for c in cols:
        m, per = c8env.c5.metrics(o.assign(pred=o[f'B9_{c}']))
        m['sets_lower_mae_vs_B5'] = int(sum(per[s]['mae_pp'] < per0[s]['mae_pp'] for s in per))
        m['mae_gain_vs_B5_pp'] = res['B5']['pooled_mae_pp'] - m['pooled_mae_pp']
        m['rare_mythic_mae_pp'] = float((o.loc[o.rarity_ord >= 2, f'B9_{c}'] - o.loc[o.rarity_ord >= 2, 'actual_gih']).abs().mean() * 100)
        res[f'B9_{c}'] = m
    res['B5']['rare_mythic_mae_pp'] = float((o.loc[o.rarity_ord >= 2, 'pred'] - o.loc[o.rarity_ord >= 2, 'actual_gih']).abs().mean() * 100)
    return res, o


def main():
    pw = pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')[['set', 'pair', 'wr_c']].rename(columns={'wr_c': 'y'})
    prod = pd.read_csv(ROOT / 'research/deck_model/pair_features.csv')[['set', 'pair', 'F0', 'F0s']]
    f = d_b5_features().merge(objective_features(), on=['set', 'pair']).merge(pw, on=['set', 'pair']).merge(prod, on=['set', 'pair'])
    t = f.reset_index(drop=True)
    assert t['set'].nunique() == 26 and len(t) == 260
    t['F0_B5s'] = dm.loso_scale(t, 'F0_B5')
    t['D_B5'] = dm.loso_ridge(t, FEATS, dm.ALPHA)
    t['P9'] = dm.loso_ridge(t, FEATS + P9F, dm.ALPHA)
    t['P_only'] = dm.loso_ridge(t, P9F, dm.ALPHA)
    r0 = rho(t, 'F0')
    res = {}
    for c, mae_col in [('F0', 'F0s'), ('F0_B5', 'F0_B5s'), ('D_B5', 'D_B5'), ('P9', 'P9'), ('P_only', 'P_only')]:
        rr = rho(t, c)
        res[c] = {'spearman_mean': float(np.mean(list(rr.values()))), 'mae_pp': float((t[mae_col] - t['y']).abs().mean()),
                  'sets_better_than_F0': int(sum(rr[s] > r0[s] for s in rr))}
    res['single_feature_spearman'] = {k: float(np.mean(list(rho(t, k).values()))) for k in P9F}
    p = res['P9']
    res['rule_p9'] = {'spearman_gt_M1': p['spearman_mean'] > 0.427, 'spearman_gt_D_B5': p['spearman_mean'] > res['D_B5']['spearman_mean'],
                      'mae_lt_F0': p['mae_pp'] < 1.779, 'sets': p['sets_better_than_F0'] >= 15}
    res['rule_p9']['pass'] = all(res['rule_p9'].values())
    t['oracle'] = t['y']
    cres, o = card_stage(t, ['P9', 'F0_B5s', 'D_B5', 'oracle'])
    res['card'] = cres
    c = cres['B9_P9']
    res['rule_f9'] = {'mae': c['mae_gain_vs_B5_pp'] > 0, 'spearman': c['spearman_mean'] > cres['B5']['spearman_mean'],
                      'sets': c['sets_lower_mae_vs_B5'] >= 14, 'gain': c['mae_gain_vs_B5_pp'] > 0.01}
    res['rule_f9']['pass'] = all(res['rule_f9'].values())
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    t.round(4).to_csv(HERE / 'pair_table.csv', index=False)
    o[['set', 'name', 'rarity_ord', 'actual_gih', 'pred', 'col'] + [c for c in o.columns if c.startswith(('cs_', 'B9_'))]].round(5).to_csv(
        HERE / 'card_oof.csv.gz', index=False, compression='gzip')
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
