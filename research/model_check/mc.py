"""Model-class check on the B11g feature set (B5 numerics + g3, g3_z). Tree part only, 1 seed, 28-set LOSO.
Arms: ET_abs (B10's tree: absolute target) | ET_dev (within-set deviation target) | HGB_dev (gradient boosting, deviation target)
Metric: centred within-set MAE (pp), Spearman, top-decile MAE."""
import pickle, sys, numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
S='/tmp/claude-0/-home-claude/dff9825a-7bfc-5f7b-8eda-9f709655d210/scratchpad/'
d=pd.read_pickle(S+'pool_g3.pkl'); F=pickle.load(open(S+'featlists.pkl','rb'))['b5']+['g3','g3_z']
d['yd']=d.actual_gih-d.groupby('set').actual_gih.transform('mean')
arm=sys.argv[1]; pred=np.full(len(d),np.nan)
for s in sorted(d.set.unique()):
    te=(d.set==s).to_numpy(); tr=d[~te]
    if arm.startswith('ET'):
        m=make_pipeline(SimpleImputer(strategy='median'),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=0))
    else:
        m=HistGradientBoostingRegressor(max_iter=600,learning_rate=0.03,max_leaf_nodes=15,min_samples_leaf=20,l2_regularization=1.0,random_state=0)
    y=tr.actual_gih if arm=='ET_abs' else tr.yd
    m.fit(tr[F],y); pred[te]=m.predict(d.loc[te,F])
d[['set','name','actual_gih','yd']].assign(pred=pred).to_csv(f'oof_{arm}.csv.gz',index=False)
print(arm,'done')
