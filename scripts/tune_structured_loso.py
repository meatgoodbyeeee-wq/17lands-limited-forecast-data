#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
CANDS=[(12,.8),(8,.8),(18,.8),(12,.6),(12,1.0),(8,.6),(8,1.0),(18,.6)]

def metrics(y,p):
    return {"mae_pp":float(np.mean(np.abs(y-p))*100),"spearman":float(spearmanr(y,p).statistic)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    d=pd.read_csv(a.input);d["set"]=d["set"].str.upper()
    if "FIN" in set(d["set"]): raise SystemExit("FIN contamination")
    nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
    results=[]
    for leaf,mf in CANDS:
        pred=np.zeros(len(d))
        for hold in sorted(d["set"].unique()):
            tr=d["set"]!=hold;te=~tr
            m=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=350,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260922))
            m.fit(d.loc[tr,nums],d.loc[tr,"actual_gih"])
            pred[te]=m.predict(d.loc[te,nums])
        z=metrics(d.actual_gih.to_numpy(),pred);z.update({"min_samples_leaf":leaf,"max_features":mf});results.append(z)
        print(z)
    results=sorted(results,key=lambda x:(x["mae_pp"],-x["spearman"]))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({"fin_used":False,"results":results},indent=2))
    print("BEST",results[0]);print("FIN_USED=false")
if __name__=="__main__":main()
