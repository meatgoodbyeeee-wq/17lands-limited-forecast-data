"""E1 top-card metric (Rule F18, see PLAN.md). python3 e1.py"""
import json
from pathlib import Path
import numpy as np, pandas as pd
R = Path(__file__).resolve().parents[1]
F = {'prod_C3': 'production_c3/oof_28set.csv.gz', 'B10': 'c9_power_questions/oof_B10.csv.gz', 'B11': 'c10_reasoned_rejudge/oof_B11.csv.gz',
     'B12': 'c11_set_reading_synergy/oof_B12.csv.gz', 'B13': 'c12_conditional_value/oof_B13.csv.gz', 'B13r': 'c12_conditional_value/oof_B13r.csv.gz',
     'B14': 'c14_context_power/oof_B14.csv.gz', 'B15r': 'a2_forced_deck_ev/oof_B15r.csv.gz', 'B15a': 'a2_forced_deck_ev/oof_B15a.csv.gz',
     'B16r': 'a3_simulated_p/oof_B16r.csv.gz', 'B16a': 'a3_simulated_p/oof_B16a.csv.gz',
     'shuf_B13': 'c12_conditional_value/oof_shuf_B13.csv.gz', 'shuf_B13r': 'c12_conditional_value/oof_shuf_B13r.csv.gz',
     'shuf_B15r': 'a2_forced_deck_ev/oof_shuf_B15r.csv.gz', 'shuf_B15a': 'a2_forced_deck_ev/oof_shuf_B15a.csv.gz',
     'shuf_B16r': 'a3_simulated_p/oof_shuf_B16r.csv.gz', 'shuf_B16a': 'a3_simulated_p/oof_shuf_B16a.csv.gz'}
CTRL = {'B13': 'shuf_B13', 'B13r': 'shuf_B13r', 'B15r': 'shuf_B15r', 'B15a': 'shuf_B15a', 'B16r': 'shuf_B16r', 'B16a': 'shuf_B16a'}
NAMED = ['Avengers Assemble!', 'Rite of the Dragoncaller', 'Smile at Death', 'Agent Phil Coulson', 'Doubling Season', 'Arahbo, the First Fang', 'Necroduality', 'Chronicle of Victory']


def per_set(df):
    out = {}
    for s, g in df.groupby('set'):
        g = g.reset_index(drop=True); d = (g.pred - g.actual_gih) * 100
        top = g.actual_gih.rank(ascending=False, method='first') <= 10; bot = g.actual_gih.rank(method='first') <= 10
        pr = g.pred.rank(ascending=False, method='first')
        out[s] = {'t_bias': d[top].mean(), 't_mae': d[top].abs().mean(), 'hit20': float((pr[top] <= 20).mean()), 'hit10': float((pr[top] <= 10).mean()),
                  'b_bias': d[bot].mean(), 'f_bias': -d[pr <= 10].mean(), 'mae': d.abs().mean(), 'n': len(g),
                  'spearman': g.pred.corr(g.actual_gih, method='spearman')}
    return pd.DataFrame(out).T


def main():
    P = {k: per_set(pd.read_csv(R / v)) for k, v in F.items() if (R / v).exists()}
    res = {}
    for k, p in P.items():
        n = p.n
        res[k] = {'t_bias': float(p.t_bias.mean()), 't_mae': float(p.t_mae.mean()), 'hit20': float(p.hit20.mean()), 'hit10': float(p.hit10.mean()),
                  'b_bias': float(p.b_bias.mean()), 'f_bias': float(p.f_bias.mean()), 'pooled_mae': float((p.mae * n).sum() / n.sum()), 'spearman': float(p.spearman.mean())}
    b = P['B10']
    for k, p in P.items():
        res[k]['sets_t_mae_lower'] = int((p.t_mae < b.t_mae).sum()); res[k]['t_mae_gain'] = res['B10']['t_mae'] - res[k]['t_mae']
    rule = {}
    for k in P:
        if k in ('B10', 'prod_C3') or k.startswith('shuf_'): continue
        r, b10 = res[k], res['B10']
        c = {'t_mae': r['t_mae'] < b10['t_mae'], 'hit20': r['hit20'] >= b10['hit20'], 't_bias': abs(r['t_bias']) < abs(b10['t_bias']),
             'sets': r['sets_t_mae_lower'] >= 15, 'mae_guard': r['pooled_mae'] - b10['pooled_mae'] <= 0.01, 'f_bias_guard': r['f_bias'] - b10['f_bias'] <= 0.5}
        if k in CTRL and CTRL[k] in res: c['control'] = res[CTRL[k]]['t_mae_gain'] < r['t_mae_gain'] / 2
        c['pass'] = all(c.values()); rule[k] = c
    res['rule_f18'] = rule
    cards = {}
    base = pd.read_csv(R / F['B10']); base['k'] = base.set + '|' + base.name
    for n in NAMED:
        g = base[base.name == n]
        if not len(g): continue
        s = g.set.iloc[0]; row = {'set': s, 'actual': float(g.actual_gih.iloc[0] * 100)}
        for k in ['B10', 'B15r', 'B16r', 'B14']:
            if k not in F or not (R / F[k]).exists(): continue
            d = pd.read_csv(R / F[k]); d = d[d.set == s].reset_index(drop=True)
            i = d.index[d.name == n][0]; row[k] = float(d.pred[i] * 100); row[k + '_rank'] = int(d.pred.rank(ascending=False)[i])
        row['actual_rank'] = int(base[base.set == s].actual_gih.rank(ascending=False)[g.index[0]]); cards[n] = row
    res['named'] = cards
    json.dump(res, open(Path(__file__).parent / 'result.json', 'w'), indent=1, default=float)
    t = pd.DataFrame({k: res[k] for k in P}).T; print(t.round(3).to_string()); print(json.dumps(rule, indent=0)); print(json.dumps(cards, indent=0))


if __name__ == '__main__':
    main()
