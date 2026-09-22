#!/usr/bin/env python3
"""FIN-blind audit of prediction compression and tail errors."""
import argparse,json
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
def metrics(y,p):
 return {"mae_pp":float(np.mean(np.abs(y-p))*100),"spearman":float(spearmanr(y,p).statistic),"actual_sd_pp":float(np.std(y)*100),"pred_sd_pp":float(np.std(p)*100),"sd_ratio":float(np.std(p)/np.std(y)),"actual_p10":float(np.quantile(y,.1)*100),"pred_p10":float(np.quantile(p,.1)*100),"actual_p90":float(np.quantile(y,.9)*100),"pred_p90":float(np.quantile(p,.9)*100)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--input",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 d=pd.read_csv(a.input);d["set"]=d["set"].str.upper();sets=set(d["set"])
 if "FIN" in sets or not sets<=DEV: raise SystemExit("FIN contamination")
 nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
 pred=np.full(len(d),np.nan);txt=d["oracle_text"].fillna("")+" TYPE "+d["type_line"].fillna("")
 for hold in sorted(sets):
  tr=d["set"]!=hold;te=~tr;y=d.loc[tr,"actual_gih"]
  tree=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
  tree.fit(d.loc[tr,nums],y);pt=tree.predict(d.loc[te,nums])
  text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
  text.fit(txt[tr],y);px=text.predict(txt[te])
  raw=.7*pt+.3*px;center=float(y.mean());pred[te]=center+1.25*(raw-center)
 d["pred"]=pred;d["resid_pp"]=(d.actual_gih-d.pred)*100
 folds={};tail={}
 for s,g in d.groupby("set"):
  folds[s]=metrics(g.actual_gih.to_numpy(),g.pred.to_numpy())
  lo=g.actual_gih.quantile(.1);hi=g.actual_gih.quantile(.9)
  for label,m in [("bottom10",g.actual_gih<=lo),("middle80",(g.actual_gih>lo)&(g.actual_gih<hi)),("top10",g.actual_gih>=hi)]:
   z=g[m];tail.setdefault(label,[]).append({"set":s,"n":len(z),"bias_pp":float(z.resid_pp.mean()),"mae_pp":float(z.resid_pp.abs().mean())})
 summary={k:{"n":int(sum(x["n"] for x in v)),"mean_bias_pp":float(np.average([x["bias_pp"] for x in v],weights=[x["n"] for x in v])),"mean_mae_pp":float(np.average([x["mae_pp"] for x in v],weights=[x["n"] for x in v]))} for k,v in tail.items()}
 out={"fin_used":False,"overall":metrics(d.actual_gih.to_numpy(),d.pred.to_numpy()),"tail_summary":summary,"folds":folds}
 open(a.out,"w").write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
