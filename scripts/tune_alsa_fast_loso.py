#!/usr/bin/env python3
"""Focused FIN-blind ALSA sweep on cached 22-set development data."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
DROP={"actual_gih","gih_wr","gih_wr_pct","gih_games","gih_wins","actual_alsa","collector_number"}
def cols(d):
    return [c for c in d.columns if c not in DROP|{"set","name","oracle_text","type_line","window_start","window_end","rarity"} and pd.api.types.is_numeric_dtype(d[c])]
def candidates():
    out=[]
    for loss in ["squared_error","absolute_error"]:
      for lr in [.04,.06,.08]:
        for l2 in [2,8]:
          out.append((f"hist_{loss}_lr{lr}_l2{l2}",dict(loss=loss,max_iter=250,learning_rate=lr,l2_regularization=l2,random_state=20260923)))
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--features",type=Path,required=True); ap.add_argument("--alsa",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args()
    f=pd.read_csv(a.features); y=pd.read_csv(a.alsa)
    if "FIN" in set(f["set"].astype(str).str.upper()) or "FIN" in set(y["set"].astype(str).str.upper()): raise SystemExit("FIN contamination detected")
    d=f.merge(y,on=["set","name"],how="inner"); base=cols(d)
    # Rarity is known pre-release. Add one-hot rarity interactions without splitting into small models.
    rarity=pd.get_dummies(d.get("rarity",pd.Series("unknown",index=d.index)).fillna("unknown").astype(str),prefix="rarity",dtype=float)
    X=pd.concat([d[base].reset_index(drop=True),rarity.reset_index(drop=True)],axis=1)
    yy=d.actual_alsa.to_numpy(float); results=[]
    for name,kw in candidates():
      p=np.full(len(d),np.nan)
      for hold in sorted(d["set"].unique()):
        tr=(d["set"]!=hold).to_numpy(); te=~tr
        m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingRegressor(**kw))
        m.fit(X.loc[tr],d.loc[tr,"actual_alsa"]); p[te]=m.predict(X.loc[te])
      ok=np.isfinite(p)&np.isfinite(yy)
      mae=float(np.mean(np.abs(p[ok]-yy[ok]))); sp=float(spearmanr(yy[ok],p[ok]).statistic)
      per={s:float(np.mean(np.abs(p[(d["set"]==s)&ok]-yy[(d["set"]==s)&ok]))) for s in sorted(d["set"].unique())}
      rmae={}
      if "rarity" in d.columns:
        for r in sorted(d["rarity"].dropna().astype(str).unique()):
          z=(d["rarity"].astype(str)==r).to_numpy()&ok
          if z.any(): rmae[r]=float(np.mean(np.abs(p[z]-yy[z])))
      z={"name":name,"mae":mae,"spearman":sp,"pred_min":float(p[ok].min()),"pred_max":float(p[ok].max()),"pred_le_1":int((p[ok]<=1).sum()),"pred_lt_1_05":int((p[ok]<1.05).sum()),"rarity_mae":rmae,"set_mae":per}
      results.append(z); print("ALSA_SWEEP",name,"MAE",mae,"SPEARMAN",sp,"LE1",z["pred_le_1"])
    results.sort(key=lambda z:(z["mae"],-z["spearman"]))
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps({"fin_used":False,"n":len(d),"results":results},indent=2),encoding="utf-8")
    print("FIN_USED=false"); print("ALSA_BEST",json.dumps(results[0]))
if __name__=="__main__": main()
