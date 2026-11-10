"""Q2: forward validation with recency weights (FDN..HOB). python3 -W ignore q2.py"""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
H = Path(__file__).resolve().parent; R = H.parents[1]
for p in ('g3_retrain', 'c9_power_questions', 'gih_llm_extract'):
    sys.path.insert(0, str(R/'research'/p))
import b11
c9 = b11.c9; c5, e = c9.c5, c9.e
ORDER = 'KHM STX AFR MID VOW NEO SNC DMU BRO ONE MOM LTR WOE LCI MKM OTJ BLB DSK FDN DFT TDM EOE TLA ECL TMT SOS MSH HOB'.split()
IDX = {s: i for i, s in enumerate(ORDER)}

def predict(train, test, nums, w=None):
    """w None -> unweighted fits and plain mean. Else sample_weight array aligned with train."""
    y = train['actual_gih']; out = []
    for sd in c9.SEEDS:
        tree = make_pipeline(SimpleImputer(strategy='median'), ExtraTreesRegressor(n_estimators=600, min_samples_leaf=8, max_features=.6, n_jobs=-1, random_state=sd))
        text = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=12000, sublinear_tf=True), Ridge(alpha=10))
        if w is None:
            tree.fit(train[nums], y); text.fit(train['__text'], y); c = float(y.mean())
        else:
            tree.fit(train[nums], y, extratreesregressor__sample_weight=w); text.fit(train['__text'], y, ridge__sample_weight=w)
            c = float(np.average(y, weights=w))
        out.append(c + 1.25*(.7*tree.predict(test[nums]) + .3*text.predict(test['__text']) - c))
    return np.mean(out, axis=0)

def stats(d, pc):
    d = d.assign(e=(d[pc] - d.actual_gih).abs()*100); per = {}
    for s in ORDER[18:]:
        g = d[d['set'] == s]
        per[s] = {'mae': float(g.e.mean()), 'spearman': float(spearmanr(g[pc], g.actual_gih)[0]),
                  'top_decile_mae': float(g.nlargest(max(1, len(g)//10), 'actual_gih').e.mean())}
    return {'per_set': per, 'mean_mae': float(np.mean([v['mae'] for v in per.values()])), 'mean_spearman': float(np.mean([v['spearman'] for v in per.values()])),
            'pooled_mae': float(d.e.mean()), 'top_decile_mae_mean': float(np.mean([v['top_decile_mae'] for v in per.values()]))}

def main():
    t0 = time.time()
    pool, base, cols = c9.load_pool()
    assert sorted(pool['set'].unique()) == sorted(ORDER)
    pool = pool.merge(b11.g3_table(), on='key', how='left'); assert pool.g3.isna().mean() < 0.01
    pool[['g3', 'g3_z']] = pool[['g3', 'g3_z']].fillna(pool.groupby('set').g3.transform('mean')).fillna(0)
    nums = c5.arm_nums('B5', base, cols) + ['g3', 'g3_z']
    oof = pd.read_csv(H.parent/'g3_retrain/oof_B11g.csv.gz'); assert len(oof) == len(pool)
    # mandatory check
    te = (pool['set'] == 'HOB').to_numpy()
    p = predict(pool[~te], pool[te], nums); diff = float(np.abs(p - oof.pred[te].to_numpy()).max())
    print('HOB LOSO check maxabsdiff', diff, flush=True)
    if not diff < 1e-9:
        json.dump({'check_maxabsdiff': diff, 'status': 'FAILED'}, open(H/'result_q2.json', 'w')); print('CHECK FAILED'); sys.exit(1)
    d = pool[['set', 'name', 'rarity_ord', 'actual_gih']].copy().reset_index(drop=True); d['pred_loso'] = oof.pred.to_numpy()
    for a_ in ('W0', 'W8', 'W4'): d['pred_' + a_] = np.nan
    pidx = pool['set'].map(IDX).to_numpy()
    for s in ORDER[18:]:
        t = IDX[s]; tr = pidx < t; tem = (pool['set'] == s).to_numpy()
        train, test = pool[tr], pool[tem]; a = (t - pidx[tr] - 1).astype(float)
        for arm, w in (('W0', None), ('W8', 0.5**(a/8)), ('W4', 0.5**(a/4))):
            d.loc[tem, 'pred_' + arm] = predict(train, test, nums, w)
        print(s, 'done', round(time.time() - t0), flush=True)
    d.to_csv(H/'oof_q2.csv.gz', index=False, compression='gzip')
    sub = d[d['set'].isin(ORDER[18:])]
    out = {'check_hob_loso_maxabsdiff': diff, 'arms': {}}
    for arm, pc in (('W0', 'pred_W0'), ('W8', 'pred_W8'), ('W4', 'pred_W4'), ('LOSO', 'pred_loso')):
        out['arms'][arm] = stats(sub, pc)
    w0 = out['arms']['W0']
    for arm in ('W8', 'W4', 'LOSO'):
        r = out['arms'][arm]; r['sets_mae_lower_than_W0'] = int(sum(r['per_set'][s]['mae'] < w0['per_set'][s]['mae'] for s in ORDER[18:]))
    out['arms']['W0']['sets_mae_lower_than_W0'] = 0
    out['loso_minus_W0_mae_pp'] = out['arms']['LOSO']['mean_mae'] - w0['mean_mae']
    rule = {}
    for arm in ('W8', 'W4'):
        r = out['arms'][arm]
        c1 = r['mean_mae'] <= w0['mean_mae'] - 0.01; c2 = r['mean_spearman'] >= w0['mean_spearman'] - 0.002; c3 = r['sets_mae_lower_than_W0'] >= 7
        rule[arm] = {'cond1_mae_improve_ge_0.01pp': bool(c1), 'mae_gain_pp': w0['mean_mae'] - r['mean_mae'], 'cond2_spearman_not_worse_than_0.002': bool(c2),
                     'spearman_diff': r['mean_spearman'] - w0['mean_spearman'], 'cond3_sets_better_ge_7': bool(c3), 'verdict': 'supported' if (c1 and c2 and c3) else 'not supported'}
    ok = [a for a in rule if rule[a]['verdict'] == 'supported']
    rule['final'] = ('supported (' + max(ok, key=lambda a: rule[a]['mae_gain_pp']) + ')') if ok else 'not supported'
    out['rule_q2'] = rule; out['runtime_s'] = time.time() - t0
    json.dump(out, open(H/'result_q2.json', 'w'), indent=1); print(json.dumps(out, indent=1))
main()
