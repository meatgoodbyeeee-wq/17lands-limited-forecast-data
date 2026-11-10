"""Q4: G3 pass-count mismatch (TMT, ECL). python3 -W ignore q4.py"""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
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
G = R/'research/g3_expert_grade'

def fit_models(train, nums, seed):
    y = train['actual_gih']
    tree = make_pipeline(SimpleImputer(strategy='median'), ExtraTreesRegressor(n_estimators=600, min_samples_leaf=8, max_features=.6, n_jobs=-1, random_state=seed))
    tree.fit(train[nums], y)
    text = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=12000, sublinear_tf=True), Ridge(alpha=10))
    text.fit(train['__text'], y)
    return float(y.mean()), tree, text

def main():
    t0 = time.time()
    pool, base, cols = c9.load_pool()
    assert sorted(pool['set'].unique()) == sorted(ORDER), sorted(pool['set'].unique())
    pool = pool.merge(b11.g3_table(), on='key', how='left'); assert pool.g3.isna().mean() < 0.01
    pool[['g3', 'g3_z']] = pool[['g3', 'g3_z']].fillna(pool.groupby('set').g3.transform('mean')).fillna(0)
    nums = c5.arm_nums('B5', base, cols) + ['g3', 'g3_z']
    oof = pd.read_csv(H.parent/'g3_retrain/oof_B11g.csv.gz'); assert len(oof) == len(pool)
    res, preds = {}, []
    for S in ('TMT', 'ECL'):
        te = (pool['set'] == S).to_numpy(); train, test = pool[~te], pool[te].copy()
        key = pd.read_csv(G/'keys_all'/f'{S}.csv')
        gs = {}
        for i in (1, 2, 3):
            d = json.load(open(G/S/f'pass{i}.json')); k = key.copy(); k['g3'] = k.tid.map(d).astype(float)
            assert k.g3.notna().all(), (S, i)
            gs[f'pass{i}'] = k.set_index('key').g3
        gs['mean3'] = pd.concat([gs['pass1'], gs['pass2'], gs['pass3']], axis=1).mean(axis=1)
        n_unj = int((~test.key.isin(gs['pass1'].index)).sum())
        variants = {}
        for v, ser in gs.items():
            mu, sd = ser.mean(), ser.std()
            g3 = test.key.map(ser); z = (test.key.map(ser) - mu)/sd
            variants[v] = (g3.fillna(mu).to_numpy(), z.fillna(mu).to_numpy())  # mirrors b11: both filled with set mean of g3
        P = {v: [] for v in variants}
        for sd_ in c9.SEEDS:
            c, tree, text = fit_models(train, nums, sd_)
            for v, (g3, z) in variants.items():
                tt = test.copy(); tt['g3'] = g3; tt['g3_z'] = z
                P[v].append(c + 1.25*(.7*tree.predict(tt[nums]) + .3*text.predict(tt['__text']) - c))
            print(S, sd_, flush=True)
        P = {v: np.mean(p, axis=0) for v, p in P.items()}
        ref = oof[(oof['set'] == S).to_numpy()].pred.to_numpy()
        diff = float(np.abs(P['pass1'] - ref).max()); print(S, 'max abs diff pass1 vs oof_B11g', diff, flush=True)
        res[S] = {'n_cards': int(len(test)), 'n_unjudged_filled': n_unj, 'check_maxabsdiff_pass1': diff, 'variants': {}}
        if not diff < 1e-9:
            json.dump(res, open(H/'result_q4.json', 'w'), indent=1); print('CHECK FAILED'); sys.exit(1)
        names = list(gs)
        res[S]['g3_pearson'] = {f'{a}-{b}': float(pearsonr(gs[a], gs[b])[0]) for i, a in enumerate(names) for b in names[i+1:]}
        for v, p in P.items():
            g = test[['set', 'name', 'rarity_ord', 'actual_gih']].assign(pred=p); g['e'] = (g.pred - g.actual_gih).abs()*100
            res[S]['variants'][v] = {'mae_pp': float(g.e.mean()), 'spearman': float(spearmanr(g.pred, g.actual_gih)[0]), 'pred_sd_pp': float(g.pred.std()*100),
                                     'top_decile_mae_pp': float(g.nlargest(max(1, len(g)//10), 'actual_gih').e.mean())}
            preds.append(g.drop(columns='e').assign(variant=v))
    pd.concat(preds).to_csv(H/'pred_q4.csv.gz', index=False, compression='gzip')
    res['runtime_s'] = time.time() - t0
    json.dump(res, open(H/'result_q4.json', 'w'), indent=1); print(json.dumps(res, indent=1))
main()
