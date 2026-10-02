"""Deck colour step 3: draft simulation, Rule S (see PLAN.md).

  python3 research/draft_sim/draft_sim.py
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/deck_model'))
import deck_model as dm  # noqa: E402

PAIRS = dm.PAIRS
COLS = "WUBRG"
PODS, SEED, GAMMA, GAMMA_SENS = 300, 20261002, 4.0, [2.0, 8.0]


def prep(g, vcol):
    v = g[vcol].values.astype(float) * 100
    colmask = np.array([[c in cs for c in COLS] for cs in g['colors']], bool)   # n x 5
    ncol = colmask.sum(1)
    land = g['type_land'].values == 1
    fitpair = np.array([[(ncol[i] > 0 and all(c in p for c in g['colors'].iloc[i])) or (ncol[i] == 0 and not land[i])
                         for p in PAIRS] for i in range(len(g))], bool)       # n x 10
    rar = g['rarity_ord'].values
    idx = {r: np.where(rar == r)[0] for r in range(4)}
    return v, colmask, ncol, fitpair, idx


def open_pack(rng, idx):
    c = rng.choice(idx[0], 10, replace=len(idx[0]) < 10)
    u = rng.choice(idx[1], 3, replace=len(idx[1]) < 3)
    rare_pool = idx[3] if (len(idx[3]) and rng.random() < 1 / 8) or not len(idx[2]) else idx[2]
    return list(c) + list(u) + [rng.choice(rare_pool)]


def simulate(g, vcol, gamma, rng):
    v, colmask, ncol, fitpair, idx = prep(g, vcol)
    m = np.median(v)
    pos = np.maximum(v - m, 0)
    played = {p: [] for p in range(10)}
    allvals = np.zeros(10)
    nall = 0
    for _ in range(PODS):
        picks = [[] for _ in range(8)]
        W = np.zeros((8, 5))
        for pk in range(3):
            packs = [open_pack(rng, idx) for _ in range(8)]
            direction = 1 if pk % 2 == 0 else -1
            for _pick in range(14):
                for d in range(8):
                    pack = packs[d]
                    tot = W[d].sum()
                    cards = np.array(pack)
                    if tot > 0:
                        s = W[d] / tot
                        cm = colmask[cards]
                        nc = ncol[cards]
                        mean_s = np.where(nc > 0, (cm * s).sum(1) / np.maximum(nc, 1), 0.5)
                        bonus = np.minimum(2 * mean_s, 1.0)
                    else:
                        bonus = np.zeros(len(cards))
                    j = int(np.argmax(v[cards] - m + gamma * bonus))
                    card = pack.pop(j)
                    picks[d].append(card)
                    W[d] += colmask[card] * pos[card]
                packs = [packs[(d - direction) % 8] for d in range(8)]
        for d in range(8):
            p = np.array(picks[d])
            vals = np.zeros(10)
            for k in range(10):
                vv = np.sort(v[p[fitpair[p, k]]])[::-1][:23]
                vals[k] = (vv.sum() + (23 - len(vv)) * (m - 3)) / 23
            best = int(np.argmax(vals))
            played[best].append(vals[best])
            allvals += vals
            nall += 1
    out = {}
    for k, pair in enumerate(PAIRS):
        out[pair] = (np.mean(played[k]) if len(played[k]) >= 20 else allvals[k] / nall, len(played[k]) / nall)
    return out


def run(cards, vcol, gamma):
    rng = np.random.default_rng(SEED)
    rows = []
    for s, g in cards.groupby('set'):
        g = g.reset_index(drop=True)
        for pair, (sc, share) in simulate(g, vcol, gamma, rng).items():
            rows.append({'set': s, 'pair': pair, 'S': sc, 'share': share, 'fallback': share * PODS * 8 < 20})
    t = pd.DataFrame(rows)
    t['S'] = t['S'] - t.groupby('set')['S'].transform('mean')
    return t


def evaluate(t, col):
    rho = dm.per_set_rho(t, col)
    sc = dm.loso_scale(t, col)
    return rho, float(np.mean(list(rho.values()))), float((sc - t['y']).abs().mean())


def main():
    cards = dm.load_cards()
    pw = pd.read_csv(ROOT / 'research/deck_pair/pair_wr.csv')
    cards = cards[cards['set'].isin(pw['set'].unique())]
    base = pd.read_csv(ROOT / 'research/deck_model/pair_features.csv')[['set', 'pair', 'F0', 'y']]
    res = {'pods': PODS, 'gamma': GAMMA}
    variants = {'S': ('pred', GAMMA), **{f'S_g{g}': ('pred', g) for g in GAMMA_SENS}, 'S_actual': ('actual_gih', GAMMA)}
    tabs = {}
    for name, (vcol, gamma) in variants.items():
        t = run(cards, vcol, gamma).merge(base, on=['set', 'pair'])
        assert len(t) == 260
        tabs[name] = t
        rho, mrho, mae = evaluate(t, 'S')
        res[name] = {'spearman_mean': mrho, 'mae_pp': mae, 'fallback_pairs': int(t['fallback'].sum())}
        if name == 'S':
            rho0, m0, mae0 = evaluate(t, 'F0')
            res['F0'] = {'spearman_mean': m0, 'mae_pp': mae0}
            res['S']['sets_better'] = int(sum(rho[s] > rho0[s] for s in rho))
            res['per_set'] = {s: {'F0': rho0[s], 'S': rho[s]} for s in rho}
            # simulated popularity vs real unsplashed deck counts
            g = pw[['set', 'pair', 'games']].copy()
            g['real_share'] = g['games'] / g.groupby('set')['games'].transform('sum')
            mm = t.merge(g, on=['set', 'pair'])
            res['popularity_spearman_mean'] = float(np.mean([spearmanr(x['share'], x['real_share']).correlation for _, x in mm.groupby('set')]))
            res['real_popularity_vs_wr_spearman_mean'] = float(np.mean([spearmanr(x['real_share'], x['y']).correlation for _, x in mm.groupby('set')]))
    r = res
    r['rule_s'] = {'spearman_gain': r['S']['spearman_mean'] - r['F0']['spearman_mean'] >= 0.05,
                   'sets': r['S']['sets_better'] >= 15, 'mae': r['S']['mae_pp'] < r['F0']['mae_pp']}
    r['rule_s']['pass'] = all(r['rule_s'].values())
    json.dump(r, open(HERE / 'result.json', 'w'), indent=1)
    pd.concat([t.assign(variant=k) for k, t in tabs.items()]).round(4).to_csv(HERE / 'sim_pairs.csv', index=False)
    print(json.dumps({k: v for k, v in r.items() if k != 'per_set'}, indent=1))


if __name__ == '__main__':
    main()
