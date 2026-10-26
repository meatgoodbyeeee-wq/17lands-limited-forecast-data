"""DA1 part B: B10 features/code, target = deck-adjusted GIH centred within set. python3 da1_b.py [verify]"""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'c9_power_questions'))
import c9
from c9 import c5, e
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline


def parts_both(train, test, nums, seed, ytr):
    """Same as export_gih_c3_28set.parts (y replaced), plus in-sample predictions of the training rows."""
    tree = make_pipeline(SimpleImputer(strategy='median'),
                         ExtraTreesRegressor(n_estimators=600, min_samples_leaf=8, max_features=.6, n_jobs=-1, random_state=seed))
    tree.fit(train[nums], ytr)
    text = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=12000, sublinear_tf=True), Ridge(alpha=10))
    text.fit(train['__text'], ytr)
    c = float(np.mean(ytr))
    f = lambda t, x: c + 1.25 * (.7 * t + .3 * x - c)
    return f(tree.predict(test[nums]), text.predict(test['__text'])), f(tree.predict(train[nums]), text.predict(train['__text']))


def main():
    pool, base, cols = c9.load_pool()
    pool = pool.copy()
    d = pd.read_csv(HERE / 'data/da1_cards.csv.gz')
    d['dadj'] = d.dadj_sum / d.dadj_n
    m = pool[['set', 'name', 'actual_gih']].merge(d[['set', 'card_name', 'dadj', 'gih_games', 'gih_wins']], left_on=['set', 'name'], right_on=['set', 'card_name'], how='left')
    assert len(m) == len(pool) and m.dadj.notna().all(), m.dadj.isna().sum()
    dif = (m.gih_wins / m.gih_games - pool.actual_gih.to_numpy()).abs().groupby(pool['set'].to_numpy()).max()
    print('max |raw GIH (DA1 file) - oof actual_gih| by set (nonzero only):', dif[dif > 1e-12].to_dict(), flush=True)
    assert set(dif[dif > 1e-12].index) <= {'HOB'}  # HOB window was still open when the stored aggregate was made
    pool['dadj'] = m.dadj.to_numpy()
    pool['y_c'] = pool.dadj - pool.groupby('set').dadj.transform('mean')
    pool['raw_c'] = pool.actual_gih - pool.groupby('set').actual_gih.transform('mean')
    b5 = c5.arm_nums('B5', base, cols)
    nums = b5 + c9.MEAN + c9.SD + c9.SUM
    o10 = pd.read_csv(HERE.parent / 'c9_power_questions/oof_B10.csv.gz')
    assert (o10.name.to_numpy() == pool.name.to_numpy()).all() and (o10.set.to_numpy() == pool.set.to_numpy()).all()
    pool['p10'] = o10.pred.to_numpy()
    out = np.full(len(pool), np.nan); fold = {}
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        S = 'HOB'; te = (pool['set'] == S).to_numpy(); tr = pool[~te]
        ps = [parts_both(tr, pool[te], nums, sd, tr.actual_gih.to_numpy())[0] for sd in c9.SEEDS]
        print('replica vs oof_B10 (HOB) max abs diff', np.abs(np.mean(ps, axis=0) - pool.loc[te, 'p10'].to_numpy()).max()); return
    for s in sorted(pool['set'].unique()):
        t0 = time.time()
        te = (pool['set'] == s).to_numpy(); tr = pool[~te]
        ytr = tr.y_c.to_numpy()
        res = [parts_both(tr, pool[te], nums, sd, ytr) for sd in c9.SEEDS]
        pt = np.mean([r[0] for r in res], axis=0); pin = np.mean([r[1] for r in res], axis=0)
        b = float((tr.raw_c * tr.y_c).sum() / (tr.y_c ** 2).sum())
        pc = pin - pd.Series(pin, index=tr.index).groupby(tr['set']).transform('mean').to_numpy()
        b_in = float((tr.raw_c.to_numpy() * pc).sum() / (pc ** 2).sum())
        fold[s] = {'b': b, 'b_insample': b_in, 'sec': time.time() - t0}
        out[te] = pt
        print(s, fold[s], flush=True)
    pool['pred_c'] = out
    pool[['set', 'name', 'rarity_ord', 'actual_gih', 'dadj', 'y_c', 'raw_c', 'p10', 'pred_c']].to_csv(HERE / 'oof_DA1_raw.csv.gz', index=False, compression='gzip')
    json.dump(fold, open(HERE / 'da1_folds.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
