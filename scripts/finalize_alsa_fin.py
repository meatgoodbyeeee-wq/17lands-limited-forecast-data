#!/usr/bin/env python3
"""Final ALSA holdout evaluation. Model choice is locked to pooled ExtraTrees from dev LOSO before FIN is read."""
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

DROP={"actual_gih","gih_wr","gih_wr_pct","gih_games","gih_wins","actual_alsa","collector_number"}
RARITY_NAMES={0:"common",1:"uncommon",2:"rare",3:"mythic"}

def cols(d):
    return [c for c in d.columns if c not in DROP|{"set","name","oracle_text","type_line","window_start","window_end"} and pd.api.types.is_numeric_dtype(d[c]) and not c.startswith("alsa_sem_")]

def model():
    return make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=350,min_samples_leaf=3,max_features=0.75,random_state=20260923,n_jobs=-1))

def metrics(d,p):
    y=d["actual_alsa"].to_numpy(float); ok=np.isfinite(y)&np.isfinite(p)
    out={"n":int(ok.sum()),"mae":float(np.mean(np.abs(p[ok]-y[ok]))),"spearman":float(spearmanr(y[ok],p[ok]).statistic),
         "actual_min":float(y[ok].min()),"actual_max":float(y[ok].max()),"pred_min":float(p[ok].min()),"pred_max":float(p[ok].max()),
         "pred_le_1_00":int((p[ok]<=1.0).sum()),"pred_lt_1_05":int((p[ok]<1.05).sum()),"pred_gt_14_0":int((p[ok]>14.0).sum())}
    out["rarity"]={}
    for r,n in RARITY_NAMES.items():
        z=ok&(d["rarity_ord"].to_numpy()==r)
        if z.any(): out["rarity"][n]={"n":int(z.sum()),"mae":float(np.mean(np.abs(p[z]-y[z]))),"pred_min":float(p[z].min()),"pred_max":float(p[z].max())}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dev-features",type=Path,required=True); ap.add_argument("--dev-alsa",type=Path,required=True); ap.add_argument("--fin-features",type=Path,required=True); ap.add_argument("--fin-alsa",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); df=pd.read_csv(a.dev_features); dy=pd.read_csv(a.dev_alsa); ff=pd.read_csv(a.fin_features); fy=pd.read_csv(a.fin_alsa)
    if "FIN" in set(df["set"].str.upper()) or "FIN" in set(dy["set"].str.upper()): raise SystemExit("FIN contamination in development data")
    if set(ff["set"].str.upper())!={"FIN"} or set(fy["set"].str.upper())!={"FIN"}: raise SystemExit("Final inputs must be FIN only")
    dev=df.merge(dy,on=["set","name"],how="inner"); fin=ff.merge(fy,on=["set","name"],how="inner")
    cs=cols(dev); m=model(); m.fit(dev[cs],dev["actual_alsa"]); p=m.predict(fin[cs])
    res={"locked_model":"pooled_extratrees_350_leaf3_maxfeatures0.75","selection_basis":"22-set FIN-blind LOSO; pooled won MAE and Spearman","fin":metrics(fin,p)}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(res,indent=2),encoding="utf-8"); print(json.dumps(res,indent=2))
if __name__=="__main__": main()
