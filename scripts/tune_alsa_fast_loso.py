#!/usr/bin/env python3
"""Fast FIN-blind ALSA candidate sweep using cached 22-set development features."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor,RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
DROP={"actual_gih","gih_wr","gih_wr_pct","gih_games","gih_wins","actual_alsa","collector_number"}
def cols(d):
    return [c for c in d.columns if c not in DROP|{"set","name","oracle_text","type_line","window_start","window_end"} and pd.api.types.is_numeric_dtype(d[c])]
def candidates():
    out=[]
    for leaf in [2,3,5,8,12]:
      for mf in [0.5,0.75,1.0]:
        out.append((f"et_l{leaf}_mf{mf}",ExtraTreesRegressor(n_estimators=220,min_samples_leaf=leaf,max_features=mf,random_state=20260923,n_jobs=-1)))
    out += [
      ("rf_l3",RandomForestRegressor(n_estimators=220,min_samples_leaf=3,max_features=0.75,random_state=20260923,n_jobs=-1)),
      ("rf_l6",RandomForestRegressor(n_estimators=220,min_samples_leaf=6,max_features=0.75,random_state=20260923,n_jobs=-1)),
      ("hist_l2",HistGradientBoostingRegressor(max_iter=250,learning_rate=.06,l2_regularization=2,random_state=20260923)),
      ("hist_l8",HistGradientBoostingRegressor(max_iter=250,learning_rate=.06,l2_regularization=8,random_state=20260923)),
    ]
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--features",type=Path,required=True); ap.add_argument("--alsa",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args()
    f=pd.read_csv(a.features); y=pd.read_csv(a.alsa)
    if "FIN" in set(f["set"].str.upper()) or "FIN" in set(y["set"].str.upper()): raise SystemExit("FIN contamination detected")
    d=f.merge(y,on=["set","name"],how="inner"); cc=cols(d); yy=d.actual_alsa.to_numpy(float)
    results=[]
    for name,est in candidates():
      p=np.full(len(d),np.nan)
      for hold in sorted(d["set"].unique()):
        tr=d["set"]!=hold; te=~tr
        m=make_pipeline(SimpleImputer(strategy="median"),est)
        m.fit(d.loc[tr,cc],d.loc[tr,"actual_alsa"]); p[te]=m.predict(d.loc[te,cc])
      ok=np.isfinite(p)&np.isfinite(yy)
      mae=float(np.mean(np.abs(p[ok]-yy[ok]))); sp=float(spearmanr(yy[ok],p[ok]).statistic)
      per={s:float(np.mean(np.abs(p[(d["set"]==s)&ok]-yy[(d["set"]==s)&ok]))) for s in sorted(d["set"].unique())}
      z={"name":name,"mae":mae,"spearman":sp,"pred_min":float(p[ok].min()),"pred_max":float(p[ok].max()),"pred_le_1":int((p[ok]<=1).sum()),"set_mae":per}
      results.append(z); print("ALSA_SWEEP",name,"MAE",mae,"SPEARMAN",sp)
    results.sort(key=lambda z:(z["mae"],-z["spearman"]))
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps({"fin_used":False,"n":len(d),"results":results},indent=2),encoding="utf-8")
    print("ALSA_BEST",json.dumps(results[0]))
if __name__=="__main__": main()
