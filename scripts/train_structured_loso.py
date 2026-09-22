#!/usr/bin/env python3
"""FIN-blind LOSO structured model. FIN must never be supplied to this script."""
import argparse,json
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

DEV={"BLB","DSK","FDN","DFT","TDM"}
LEAK={"set","name","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}

def met(y,p,k=30):
    oi=np.argsort(y); op=np.argsort(p)
    return {"mae_pp":float(np.mean(np.abs(y-p))*100),"spearman":float(spearmanr(y,p).statistic),
      "top30_recall":len(set(oi[-k:])&set(op[-k:]))/k,"bottom30_recall":len(set(oi[:k])&set(op[:k]))/k,
      "sd_ratio":float(np.std(p)/np.std(y))}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",default="model_out/dev_feature_table.csv"); ap.add_argument("--out",default="model_out/structured_loso.json"); a=ap.parse_args()
    d=pd.read_csv(a.input); sets=set(d["set"].str.upper())
    if not sets<=DEV or "FIN" in sets: raise SystemExit("Refusing non-development set / FIN contamination")
    # Color coefficients are environment-dependent; omit until color-strength forecast exists.
    f=[c for c in d.columns if c not in LEAK and not c.startswith("color_")]
    pred=np.zeros(len(d)); folds={}
    for s in sorted(sets):
      tr=d["set"]!=s; te=~tr
      m=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=700,min_samples_leaf=12,max_features=.8,n_jobs=-1,random_state=20260922))
      m.fit(d.loc[tr,f],d.loc[tr,"actual_gih"]); pred[te]=m.predict(d.loc[te,f])
      folds[s]=met(d.loc[te,"actual_gih"].to_numpy(),pred[te])
    report={"fin_used":False,"sets":sorted(sets),"features":f,"folds":folds,
      "mean_fold":{"mae_pp":float(np.mean([v["mae_pp"] for v in folds.values()])),"spearman":float(np.mean([v["spearman"] for v in folds.values()])),
      "top30_recall":float(np.mean([v["top30_recall"] for v in folds.values()])),"bottom30_recall":float(np.mean([v["bottom30_recall"] for v in folds.values()]))}}
    open(a.out,"w").write(json.dumps(report,indent=2)); print(json.dumps(report["mean_fold"],indent=2))
if __name__=="__main__": main()
