#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

TRAIN_SETS=["BLB","DSK","FDN","DFT","TDM"]
assert "FIN" not in TRAIN_SETS

def load_local(root):
    frames=[]
    for s in TRAIN_SETS:
        p=root/s/f"{s}_gih_28d.csv"
        frames.append(pd.read_csv(p))
    return pd.concat(frames,ignore_index=True)

def rank_metrics(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float)
    mae=float(np.mean(np.abs(y-p)))
    rho=pd.Series(y).corr(pd.Series(p),method="spearman")
    rho=None if pd.isna(rho) else float(rho)
    n=min(30,len(y))
    top=len(set(np.argsort(y)[-n:])&set(np.argsort(p)[-n:]))/n
    bot=len(set(np.argsort(y)[:n])&set(np.argsort(p)[:n]))/n
    return {"mae_pp":100*mae,"spearman":rho,"top30_recall":top,"bottom30_recall":bot}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--local-dir",type=Path,required=True)
    ap.add_argument("--out-dir",type=Path,default=Path("model_out"))
    a=ap.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    df=load_local(a.local_dir)
    folds=[]
    for hold in TRAIN_SETS:
        tr=df[df["set"]!=hold]; va=df[df["set"]==hold]
        pred=np.repeat(np.average(tr.gih_wr,weights=tr.gih_games),len(va))
        folds.append({"holdout":hold,**rank_metrics(va.gih_wr,pred),"n_cards":len(va)})
    report={"status":"scaffold_complete","fin_used":False,"training_sets":TRAIN_SETS,
      "evaluation":"leave-one-set-out","baseline":"weighted training-set mean only",
      "important_limitation":"Compact GIH artifacts contain outcomes but no pre-release card features. A real card-strength model cannot be improved without joining the forecast feature table.",
      "folds":folds}
    (a.out_dir/"fin_blind_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    pd.DataFrame(folds).to_csv(a.out_dir/"fin_blind_folds.csv",index=False)
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
