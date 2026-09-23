#!/usr/bin/env python3
"""FIN-blind ALSA LOSO: pooled baseline vs rarity-specialized vs rarity+visible-strength semantics."""
import argparse, json, re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

DROP={"actual_gih","gih_wr","gih_wr_pct","gih_games","gih_wins","actual_alsa","collector_number"}
RARITY_NAMES={0:"common",1:"uncommon",2:"rare",3:"mythic"}

def add_alsa_semantics(d):
    t=d["oracle_text"].fillna("").str.lower()
    typ=d["type_line"].fillna("").str.lower()
    mv=pd.to_numeric(d["mv"],errors="coerce").fillna(0)
    power=pd.to_numeric(d["power"],errors="coerce")
    d=d.copy()
    # Features intended to approximate how obviously attractive a card looks during preview/pick evaluation.
    d["alsa_sem_clean_removal"]=t.str.contains(r"destroy target|exile target|deals? [^.]* damage to (any target|target creature|target permanent)",regex=True).astype(int)
    d["alsa_sem_card_draw"]=t.str.contains(r"draw (a|one|two|three|x|that many) cards?",regex=True).astype(int)
    d["alsa_sem_evasion"]=t.str.contains(r"flying|menace|can't be blocked|cannot be blocked",regex=True).astype(int)
    d["alsa_sem_repeatable_value"]=t.str.contains(r"whenever .*draw|at the beginning of .*draw|whenever .*create .*token|at the beginning of .*create .*token",regex=True).astype(int)
    d["alsa_sem_board_sweeper"]=t.str.contains(r"destroy all|exile all|deals? [0-9x]+ damage to each creature|-\d+/-\d+ until end of turn",regex=True).astype(int)
    d["alsa_sem_dependency"]=t.str.contains(r"only if|unless|creature type|shares? a creature type|if you control|for each .* you control",regex=True).astype(int)
    d["alsa_sem_narrow"]=t.str.contains(r"target artifact or enchantment|from a graveyard|graveyard to exile|can't gain life",regex=True).astype(int)
    d["alsa_sem_eff_creature"]=((typ.str.contains("creature")) & power.notna() & (mv>0) & ((power/mv)>=1.0)).astype(int)
    return d

def feature_cols(d,semantic):
    x=add_alsa_semantics(d) if semantic else d
    cols=[]
    for c in x.columns:
        if c in DROP or c in {"set","name","oracle_text","type_line","window_start","window_end"}: continue
        if pd.api.types.is_numeric_dtype(x[c]): cols.append(c)
    if not semantic: cols=[c for c in cols if not c.startswith("alsa_sem_")]
    return x,cols

def model():
    return make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=350,min_samples_leaf=3,max_features=0.75,random_state=20260923,n_jobs=-1))

def run(d,mode):
    semantic=mode=="rarity_semantic"
    x,cols=feature_cols(d,semantic)
    preds=np.full(len(x),np.nan)
    for hold in sorted(x["set"].unique()):
        tr=x["set"]!=hold; te=~tr
        if mode=="pooled":
            m=model(); m.fit(x.loc[tr,cols],x.loc[tr,"actual_alsa"]); preds[te]=m.predict(x.loc[te,cols])
        else:
            for r in sorted(x.loc[te,"rarity_ord"].dropna().unique()):
                te_r=te & (x["rarity_ord"]==r); tr_r=tr & (x["rarity_ord"]==r)
                # Explicit rarity-specialized model; fallback to pooled only for unexpectedly sparse groups.
                use=tr_r if tr_r.sum()>=80 else tr
                m=model(); m.fit(x.loc[use,cols],x.loc[use,"actual_alsa"]); preds[te_r]=m.predict(x.loc[te_r,cols])
    y=x["actual_alsa"].to_numpy(float); ok=np.isfinite(preds)&np.isfinite(y)
    mae=float(np.mean(np.abs(preds[ok]-y[ok]))); sp=float(spearmanr(y[ok],preds[ok]).statistic)
    rarity={}
    for r,n in RARITY_NAMES.items():
        z=ok&(x["rarity_ord"].to_numpy()==r)
        if z.any(): rarity[n]={"n":int(z.sum()),"mae":float(np.mean(np.abs(preds[z]-y[z]))),"pred_min":float(preds[z].min()),"pred_max":float(preds[z].max())}
    realism={"n":int(ok.sum()),"actual_min":float(y[ok].min()),"actual_max":float(y[ok].max()),"pred_min":float(preds[ok].min()),"pred_max":float(preds[ok].max()),
             "pred_le_1_00":int((preds[ok]<=1.0).sum()),"pred_lt_1_05":int((preds[ok]<1.05).sum()),"pred_gt_14_0":int((preds[ok]>14.0).sum())}
    return {"mode":mode,"mae":mae,"spearman":sp,"rarity":rarity,"realism":realism}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--features",type=Path,required=True); ap.add_argument("--alsa",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); f=pd.read_csv(a.features); y=pd.read_csv(a.alsa)
    if "FIN" in set(f["set"].str.upper()) or "FIN" in set(y["set"].str.upper()): raise SystemExit("FIN contamination detected")
    d=f.merge(y,on=["set","name"],how="inner")
    if len(d)<1000: raise SystemExit(f"Too few matched ALSA rows: {len(d)}")
    res=[run(d,m) for m in ["pooled","rarity","rarity_semantic"]]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(res,indent=2),encoding="utf-8")
    for z in res: print("ALSA_RESULT",z["mode"],"MAE",z["mae"],"SPEARMAN",z["spearman"],"REALISM",z["realism"])
    print("matched",len(d),"sets",sorted(d["set"].unique()))

if __name__=="__main__": main()
