#!/usr/bin/env python3
"""FIN-blind LOSO text + structured ensemble. Development sets only.\nWord TF-IDF production baseline."""
import argparse,json
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import ExtraTreesRegressor
DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
def met(y,p,k=30):
 o=np.argsort(y); q=np.argsort(p); return {"mae_pp":float(np.mean(abs(y-p))*100),"spearman":float(spearmanr(y,p).statistic),"top30":len(set(o[-k:])&set(q[-k:]))/k,"bottom30":len(set(o[:k])&set(q[:k]))/k,"sd_ratio":float(np.std(p)/np.std(y))}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--input",default="model_out/dev_feature_table.csv"); ap.add_argument("--out",default="model_out/text_ensemble_loso.json"); a=ap.parse_args()
 d=pd.read_csv(a.input); sets=set(d["set"].str.upper())
 if not sets<=DEV or "FIN" in sets: raise SystemExit("FIN contamination")
 nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
 pred=np.zeros(len(d)); chosen={}
 for hold in sorted(sets):
  tr=d["set"]!=hold; te=~tr; y=d.loc[tr,"actual_gih"]
  tree=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=12,max_features=.8,n_jobs=-1,random_state=20260922))
  tree.fit(d.loc[tr,nums],y); pt=tree.predict(d.loc[te,nums])
  txt=d["oracle_text"].fillna("")+" TYPE "+d["type_line"].fillna("")
  text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=20))
  text.fit(txt[tr],y); px=text.predict(txt[te])
  # Fixed conservative blend; no holdout-set tuning.
  raw=.7*pt+.3*px
  center=float(np.mean(y))
  p=center+1.25*(raw-center)
  pred[te]=p; chosen[hold]=met(d.loc[te,"actual_gih"].to_numpy(),p)
 out={"fin_used":False,"folds":chosen,"overall":met(d["actual_gih"].to_numpy(),pred)}
 open(a.out,"w").write(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
if __name__=="__main__":main()

