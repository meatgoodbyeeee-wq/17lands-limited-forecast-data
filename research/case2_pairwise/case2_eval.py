"""Case 2: Bradley-Terry scores from blind in-set rankings, Rule P check (HOB, MSH), frozen FRA adjustment.

Usage: python3 research/case2_pairwise/case2_eval.py [path/to/adopted-gih-fra.json.gz]
"""
import glob, gzip, json, sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W_MAIN = 0.3
W_SENS = [0.15, 0.5, 1.0]


def load_ranks():
    groups = json.load(open(HERE / 'groups.json'))
    skip = set(json.load(open(HERE / 'groups_fix.json'))['duplicate_gids_ignored'])
    ranks = {}
    for f in sorted(glob.glob(str(HERE / 'rank' / 'r*.txt'))):
        for line in open(f):
            p = line.split()
            if p:
                ranks[p[0]] = p[1]
    out = []
    for g in groups:
        if g['gid'] in skip:
            continue
        order = [g['keys'][ord(c) - 65] for c in ranks[g['gid']]]
        out.append({'gid': g['gid'], 'set': g['set'], 'rep': g['rep'], 'order': order})
    return out


def bradley_terry(cards, rankings, iters=2000, tol=1e-10):
    """MM algorithm; each card also gets 0.5 win + 0.5 loss against a virtual card of strength 1."""
    idx = {c: i for i, c in enumerate(cards)}
    n = len(cards)
    wins = np.zeros((n, n))
    for order in rankings:
        for a, b in combinations(order, 2):  # a ranked above b
            wins[idx[a], idx[b]] += 1
    games = wins + wins.T
    W = wins.sum(1) + 0.5
    p = np.ones(n)
    for _ in range(iters):
        denom = (games / (p[:, None] + p[None, :])).sum(1) + 1.0 / (p + 1.0)
        new = W / denom
        new /= np.exp(np.mean(np.log(new)))
        if np.max(np.abs(np.log(new) - np.log(p))) < tol:
            p = new
            break
        p = new
    s = np.log(p)
    return pd.Series((s - s.mean()) / s.std(ddof=0), index=cards)


def debias(z, blind):
    """Case 2b (added after Rule P failed): remove the part of BT z explained by mana value (capped at 7)
    and 'is a land', within set. Uses only card attributes, never 17Lands numbers."""
    d = blind.loc[z.index]
    X = np.column_stack([np.ones(len(d)), d['mv'].clip(upper=7), d['type_line'].str.contains('Land').astype(float)])
    r = z.values - X @ np.linalg.lstsq(X, z.values, rcond=None)[0]
    return pd.Series((r - r.mean()) / r.std(ddof=0), index=z.index)


def combine(pred, z, w):
    return (1 - w) * pred + w * (pred.mean() + pred.std(ddof=0) * z)


def metrics(pred, actual):
    return {'mae_pp': float(np.mean(np.abs(pred - actual)) * 100),
            'spearman': float(spearmanr(pred, actual).correlation)}


def main():
    ranks = load_ranks()
    fwd = pd.read_csv(ROOT / 'research/case6/forward_oof.csv.gz')
    cols = [c for c in fwd.columns if c.startswith('pred_B_extended+C3_s')]
    fwd['pred'] = fwd[cols].mean(axis=1)
    fwd['key'] = fwd['set'] + '|' + fwd['name']

    blind = pd.read_csv(HERE / 'cards_blind.csv.gz').set_index('key')
    result = {'w_main': W_MAIN, 'groups_used': len(ranks), 'sets': {}}
    zs, zb = {}, {}
    for st in ['HOB', 'MSH', 'FRA']:
        rs = [r for r in ranks if r['set'] == st]
        cards = sorted({k for r in rs for k in r['order']})
        z = bradley_terry(cards, [r['order'] for r in rs])
        zs[st] = z
        zb[st] = debias(z, blind)
        # replicate consistency: BT from each replicate alone
        reps = {}
        for rep in sorted({r['rep'] for r in rs}):
            sub = [r['order'] for r in rs if r['rep'] == rep]
            c2 = sorted({k for o in sub for k in o})
            reps[rep] = bradley_terry(c2, sub)
        rep_rho = {f'{a}v{b}': float(spearmanr(reps[a].reindex(cards), reps[b].reindex(cards), nan_policy='omit').correlation)
                   for a, b in combinations(sorted(reps), 2)}
        info = {'n_cards': len(cards), 'n_groups': len(rs), 'replicate_spearman': rep_rho}
        if st != 'FRA':
            d = fwd[fwd['set'] == st].set_index('key')
            missing = [c for c in cards if c not in d.index]
            assert not missing, missing[:5]
            d = d.loc[cards]
            a, p = d['actual_gih'].values, d['pred'].values
            zz = z.loc[cards].values
            info['pred'] = metrics(p, a)
            info['bt_alone_spearman'] = float(spearmanr(zz, a).correlation)
            info['pred_vs_bt_spearman'] = float(spearmanr(zz, p).correlation)
            info['adjusted'] = {str(w): metrics(combine(p, zz, w), a) for w in [W_MAIN] + W_SENS}
            zr = zb[st].loc[cards].values
            info['case2b_exploratory'] = {'bt_alone_spearman': float(spearmanr(zr, a).correlation),
                                          'adjusted': {str(w): metrics(combine(p, zr, w), a) for w in [W_MAIN] + W_SENS}}
        result['sets'][st] = info

    # Rule P on mean over HOB and MSH
    def mean_of(key, w=None):
        vals = []
        for st in ['HOB', 'MSH']:
            m = result['sets'][st]['pred'] if w is None else result['sets'][st]['adjusted'][str(w)]
            vals.append(m[key])
        return float(np.mean(vals))
    rp = {'pred_mae': mean_of('mae_pp'), 'pred_spearman': mean_of('spearman'),
          'adj_mae': mean_of('mae_pp', W_MAIN), 'adj_spearman': mean_of('spearman', W_MAIN)}
    rp['pass'] = bool(rp['adj_mae'] < rp['pred_mae'] and rp['adj_spearman'] > rp['pred_spearman'])
    result['rule_p'] = rp

    # FRA frozen adjustment (production prediction, gih in pp)
    src = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/limited-forecast-pages/data/adopted-gih-fra.json.gz'
    prod = json.load(gzip.open(src))
    fra = pd.DataFrame([{'key': 'FRA|' + c['id'], 'name': c['name'], 'pred_gih': c['gih']} for c in prod['cards']])
    fra = fra.drop_duplicates('key').set_index('key')
    z = zs['FRA']
    miss = sorted(set(fra.index) ^ set(z.index))
    assert not miss, miss[:5]
    fra = fra.loc[fra.index.intersection(z.index)]
    fra['bt_z'] = z.loc[fra.index]
    for w in [W_MAIN] + W_SENS:
        fra[f'adj_w{w}'] = combine(fra['pred_gih'], fra['bt_z'], w)
    fra['bt_z_2b'] = zb['FRA'].loc[fra.index]
    for w in [W_MAIN] + W_SENS:
        fra[f'adj2b_w{w}'] = combine(fra['pred_gih'], fra['bt_z_2b'], w)
    result['sets']['FRA']['production_version'] = prod['version']
    result['sets']['FRA']['pred_vs_bt_spearman'] = float(spearmanr(fra['pred_gih'], fra['bt_z']).correlation)
    fra.reset_index(drop=True).round(4).to_csv(HERE / 'fra_frozen.csv', index=False)

    allz = pd.concat([pd.DataFrame({'bt_z': z, 'bt_z_2b': zb[st], 'set': st}) for st, z in zs.items()])
    allz.index.name = 'key'
    allz.round(5).to_csv(HERE / 'bt_scores.csv')
    json.dump(result, open(HERE / 'result.json', 'w'), indent=1)
    print(json.dumps({k: result[k] for k in ['rule_p']}, indent=1))
    for st in ['HOB', 'MSH']:
        print(st, result['sets'][st]['case2b_exploratory']['adjusted'][str(W_MAIN)])


if __name__ == '__main__':
    main()
