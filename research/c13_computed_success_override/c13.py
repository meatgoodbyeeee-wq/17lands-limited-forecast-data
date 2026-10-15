"""C13 computed success probability + override of B10 (Rule F14, see PLAN.md).

  python3 c13.py features | evaluate
"""
import hashlib, importlib.util, itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import binom

HERE = Path(__file__).resolve().parent
RES = HERE.parent
C11, C12, C9 = RES / 'c11_set_reading_synergy', RES / 'c12_conditional_value', RES / 'c9_power_questions'


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


COLS = list('WUBRG')
GRID = [(m, k) for m in (0, 1, 2, 3) for k in (0.25, 0.5, 1.0)]
NAMED = ['Avengers Assemble!', 'Chronicle of Victory', 'Necroduality', 'Rite of the Dragoncaller', 'Smile at Death', 'Oko, Lorwyn Liege']


def subtypes(t):
    return set(t.split('—', 1)[1].replace('/', ' ').split()) if '—' in t else set()


def deck_options(S):
    S = set(S)
    if len(S) >= 2: return [S]
    if len(S) == 1: return [S | {x} for x in COLS if x not in S]
    return [set(a) for a in itertools.combinations(COLS, 2)]


def features():
    cards = pd.read_csv(C11 / 'set_cards.csv.gz', keep_default_na=False)
    cards['freq'] = cards['freq'].astype(float)
    r11 = {p: _load('c11chk', C11 / 'check_raw.py').load_raw(p, cards) for p in ('s1', 's2')}
    r12 = {p: _load('c12chk', C12 / 'check_raw.py').load_raw(p, cards) for p in ('s1', 's2')}
    for p in r11: assert not r11[p][1] and not r12[p][1]
    rows = []
    for s, g in cards.groupby('set'):
        g = g.reset_index(drop=True)
        nl = ~g['type'].str.contains('Land')
        cs = [set(c) for c in g['colors'].astype(str)]
        st = [subtypes(t) for t in g['type']]
        idx = {i: n for n, i in enumerate(g['id'])}
        for t in g[g['target'] == 1].itertuples():
            vals = []
            for p in ('s1', 's2'):
                _, _, D, I = r11[p][0][(s, t.id)]
                k, on, off = r12[p][0][(s, t.id)]
                E = set()
                for kind, v in D + I:
                    if kind == 'id': E.add(v)
                    else: E |= {i for i, ss in zip(g['id'], st) if v in ss}
                E.discard(t.id)
                pons = []
                for dk in deck_options(set(t.colors)):
                    ok = np.array([(not c) or c <= dk for c in cs]) & nl.to_numpy()
                    ok[idx[t.id]] = False
                    tot = g.loc[ok, 'freq'].sum()
                    en = sum(g.loc[idx[i], 'freq'] for i in E if i in idx and ok[idx[i]])
                    share = min(1.0, en / tot) if tot > 0 else 0.0
                    pons.append(1.0 if k == 0 else float(binom.sf(k - 1, 22, share)))
                pon = float(np.mean(pons)); vals.append((k, on, off, pon, pon * on + (1 - pon) * off))
            a = np.array(vals, float).mean(0)
            rows.append({'key': t.key, 'k': a[0], 'on': a[1], 'off': a[2], 'pon': a[3], 'ev': a[4], 'set': s})
    f = pd.DataFrame(rows); f.to_csv(HERE / 'c13_features.csv', index=False)
    print(len(f)); print(f[['k', 'on', 'off', 'pon', 'ev']].describe().round(3).to_string())
    print(f[f.key.str.contains('Avengers|Necroduality|Chronicle of Victory')])


def slope_of(m):
    d = m.copy()
    d['pg'] = d['p'] - d.groupby(['set', 'rarity_ord'])['p'].transform('mean')
    d['gg'] = d['g'] - d.groupby(['set', 'rarity_ord'])['g'].transform('mean')
    return float(np.polyfit(d['gg'], d['pg'], 1)[0])


def adjust(m, slope, mm, kk, ev):
    dd = ev - m['g']
    return (m['p'] + (m['tg'] * kk * slope * np.sign(dd) * np.maximum(0, np.abs(dd) - mm))).to_numpy()


def nested(m, ev):
    pred = np.zeros(len(m)); chosen = {}
    for s in sorted(m['set'].unique()):
        tr, te = m[m.set != s], m[m.set == s]
        sl = slope_of(tr)
        best = min(GRID, key=lambda c: np.abs(adjust(tr, sl, c[0], c[1], ev[tr.index]) - tr['y']).mean())
        chosen[s] = best
        pred[(m.set == s).to_numpy()] = adjust(te, sl, best[0], best[1], ev[te.index])
    return pred, chosen


def summarize(m, pred):
    sets = sorted(m.set.unique()); err = np.abs(pred - m['y'])
    sp = np.mean([pd.Series(pred[(m.set == s).to_numpy()]).corr(m.loc[m.set == s, 'y'].reset_index(drop=True), method='spearman') for s in sets])
    per = {s: float(err[(m.set == s).to_numpy()].mean()) for s in sets}
    return {'mae_pp': float(err.mean()), 'spearman_mean': float(sp)}, per


def evaluate():
    f = pd.read_csv(HERE / 'c13_features.csv').set_index('key')
    b = pd.read_csv(C9 / 'oof_B10.csv.gz'); b['key'] = b['set'] + '|' + b['name']
    c9f = pd.read_csv(C9 / 'c9_features.csv.gz').set_index('key')
    m = b.copy(); m['p'] = m['pred'] * 100; m['y'] = m['actual_gih'] * 100
    m['g'] = m['key'].map(c9f['c9_m_GRADE']); m['tg'] = m['key'].isin(f.index).astype(float)
    m['ev'] = m['key'].map(f['ev']).fillna(m['g'])
    assert m['g'].notna().all()
    res = {}
    res['B10'], perB = summarize(m, m['p'].to_numpy())[0], summarize(m, m['p'].to_numpy())[1]
    pred, chosen = nested(m, m['ev'])
    res['override'], per = summarize(m, pred)
    res['override']['sets_lower'] = int(sum(per[s] < perB[s] for s in per)); res['override']['gain_pp'] = res['B10']['mae_pp'] - res['override']['mae_pp']
    res['chosen_per_fold'] = {s: list(c) for s, c in chosen.items()}
    # shuffled control
    rng = np.random.default_rng(20261017); ev_s = m['ev'].copy()
    for s, ix in m[m.tg == 1].groupby('set').groups.items():
        ix = np.array(ix); ev_s[ix] = m.loc[rng.permutation(ix), 'ev'].to_numpy()
    pred_s, _ = nested(m, ev_s)
    res['shuffled'], per_s = summarize(m, pred_s)
    res['shuffled']['sets_lower'] = int(sum(per_s[s] < perB[s] for s in per_s)); res['shuffled']['gain_pp'] = res['B10']['mae_pp'] - res['shuffled']['mae_pp']
    o, sh = res['override'], res['shuffled']
    res['rule_f14'] = {'mae': o['mae_pp'] < res['B10']['mae_pp'], 'spearman': o['spearman_mean'] > res['B10']['spearman_mean'], 'sets': o['sets_lower'] >= 15,
                       'gain': o['gain_pp'] > 0.01, 'control': sh['gain_pp'] < o['gain_pp'] / 2}
    res['rule_f14']['pass'] = all(res['rule_f14'].values())
    # reporting
    sl_all = slope_of(m); res['slope_all'] = sl_all
    allbest = min(GRID, key=lambda c: np.abs(adjust(m, sl_all, c[0], c[1], m['ev']) - m['y']).mean())
    res['all28_best_m_kappa'] = list(allbest)
    res['all28_grid'] = {f'm{c[0]}_k{c[1]}': float(np.abs(adjust(m, sl_all, c[0], c[1], m['ev']) - m['y']).mean()) for c in GRID}
    t = m['tg'] == 1
    ae = lambda p, msk: float(np.abs(p[msk.to_numpy()] - m.loc[msk, 'y']).mean())
    res['by_target'] = {'targets': {'B10': ae(m['p'].to_numpy(), t), 'override': ae(pred, t)}, 'others': {'B10': ae(m['p'].to_numpy(), ~t), 'override': ae(pred, ~t)}}
    from sklearn.metrics import roc_auc_score
    m['arank'] = m.groupby('set')['y'].rank(ascending=False); yy = (m.arank[t] <= 15).astype(int)
    res['auc_top15_targets'] = {'B10': float(roc_auc_score(yy, m.loc[t, 'p'])), 'override': float(roc_auc_score(yy, pred[t.to_numpy()]))}
    res['pon_summary'] = f['pon'].describe().round(3).to_dict()
    named = {}
    for n in NAMED:
        r = m[m['name'] == n]
        if len(r):
            i = r.index[0]; fk = r.iloc[0]['key']
            named[n] = {'actual': float(r.iloc[0]['y']), 'B10': float(r.iloc[0]['p']), 'override': float(pred[i]), 'pon': float(f.loc[fk, 'pon']) if fk in f.index else None,
                        'ev': float(f.loc[fk, 'ev']) if fk in f.index else None, 'grade': float(r.iloc[0]['g'])}
    res['named'] = named
    json.dump(res, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    if res['rule_f14']['pass']:
        freeze_fra(allbest, sl_all)


def freeze_fra(allbest, slope):
    f = pd.read_csv(HERE / 'c13_features.csv').set_index('key')
    fp = pd.read_csv(C9 / 'fra_frozen_predictions.csv')
    c9f = pd.read_csv(C9 / 'c9_features.csv.gz').set_index('key')
    out = fp[['id', 'name', 'pred_B10']].copy(); key = 'FRA|' + out['id']
    ev = key.map(f['ev']); g = key.map(c9f['c9_m_GRADE']); d = ev - g
    adj = allbest[1] * slope * np.sign(d) * np.maximum(0, np.abs(d) - allbest[0]) / 100
    out['pred_B10ovr'] = out['pred_B10'] + adj.fillna(0)
    out['ev'] = ev; out['grade'] = g
    p = HERE / 'fra_frozen_override.csv'; out.to_csv(p, index=False)
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    json.dump({'m_kappa': list(allbest), 'slope': slope, 'sha256': h}, open(HERE / 'fra_frozen_meta.json', 'w'))
    print('FRA frozen', h, 'targets adjusted', int((adj.fillna(0) != 0).sum()))


if __name__ == '__main__':
    {'features': features, 'evaluate': evaluate}[sys.argv[1]]()
