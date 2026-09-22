#!/usr/bin/env python3
"""FIN-blind decompression sweep around the tuned ensemble."""
import argparse,json
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
DECOMP=[1.0,1.15,1.25,1.35,1.5,1.65,1.8,2.0]
def met(y,p):
 return {"mae_pp":float(np.mean(abs(y-p))*100),"spearman":float(spearmanr(y,p).statistic),"sd_ratio":float(np.std(p)/np.std(y))}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--input",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 d=pd.read_csv(a.input);d["set"]=d["set"].str.upper()
 if "FIN" in set(d["set"]):raise SystemExit("FIN contamination")
 nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
 txt=d["oracle_text"].fillna("")+" TYPE "+d["type_line"].fillna("");cache={}
 for hold in sorted(d["set"].unique()):
  tr=d["set"]!=hold;te=~tr;y=d.loc[tr,"actual_gih"]
  tree=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
  tree.fit(d.loc[tr,nums],y);pt=tree.predict(d.loc[te,nums])
  text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
  text.fit(txt[tr],y);px=text.predict(txt[te]);cache[hold]=(te,float(y.mean()),.7*pt+.3*px)
 results=[]
 for decomp in DECOMP:
  pred=np.zeros(len(d))
  for te,center,raw in cache.values():pred[te]=center+decomp*(raw-center)
  q=met(d.actual_gih.to_numpy(),pred);q["decompression"]=decomp;results.append(q);print(q)
 results.sort(key=lambda x:(x["mae_pp"],-x["spearman"]))
 open(a.out,"w").write(json.dumps({"fin_used":False,"results":results},indent=2));print("BEST",results[0]);print("FIN_USED=false")
if __name__=="__main__":main()
