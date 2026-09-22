#!/usr/bin/env python3
"""FIN-blind model-improvement experiment.

Downloads the compact artifacts from a completed aggregation run, but only for
BLB/DSK/FDN/DFT/TDM. FIN is deliberately excluded from every training,
selection and calibration path.

This stage establishes leakage-safe leave-one-set-out evaluation scaffolding.
Card-level predictive features can be joined here once the forecast feature
table is available.
"""
from __future__ import annotations
import argparse, io, json, os, urllib.request, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

TRAIN_SETS = ["BLB","DSK","FDN","DFT","TDM"]
assert "FIN" not in TRAIN_SETS

def gh_json(url, token):
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","User-Agent":"FIN-blind-experiment"})
    with urllib.request.urlopen(req) as r: return json.load(r)

def download(url, token):
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","User-Agent":"FIN-blind-experiment"})
    with urllib.request.urlopen(req) as r: return r.read()

def load_artifacts(repo, run_id, token):
    meta=gh_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100",token)
    by_name={a["name"]:a for a in meta["artifacts"]}
    frames=[]
    for s in TRAIN_SETS:
        name=f"{s}-28d"
        a=by_name[name]
        raw=download(a["archive_download_url"],token)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            with z.open(f"{s}_gih_28d.csv") as f:
                frames.append(pd.read_csv(f))
    return pd.concat(frames,ignore_index=True)

def rank_metrics(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float)
    mae=float(np.mean(np.abs(y-p)))
    rho=float(pd.Series(y).corr(pd.Series(p),method="spearman"))
    n=min(30,len(y))
    top=len(set(np.argsort(y)[-n:]) & set(np.argsort(p)[-n:]))/n
    bot=len(set(np.argsort(y)[:n]) & set(np.argsort(p)[:n]))/n
    return {"mae_pp":100*mae,"spearman":rho,"top30_recall":top,"bottom30_recall":bot}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",required=True); ap.add_argument("--run-id",type=int,required=True)
    ap.add_argument("--out-dir",type=Path,default=Path("model_out"))
    a=ap.parse_args(); token=os.environ["GITHUB_TOKEN"]; a.out_dir.mkdir(parents=True,exist_ok=True)
    df=load_artifacts(a.repo,a.run_id,token)
    # Leakage-safe baseline: training-set empirical mean. This verifies LOSO plumbing;
    # it is not presented as the final forecasting model.
    folds=[]
    for hold in TRAIN_SETS:
        tr=df[df["set"]!=hold]; va=df[df["set"]==hold]
        pred=np.repeat(np.average(tr.gih_wr,weights=tr.gih_games),len(va))
        folds.append({"holdout":hold,**rank_metrics(va.gih_wr,pred),"n_cards":len(va)})
    report={
      "status":"scaffold_complete",
      "fin_used":False,
      "training_sets":TRAIN_SETS,
      "evaluation":"leave-one-set-out",
      "baseline":"weighted training-set mean only",
      "important_limitation":"Compact GIH artifacts contain outcomes but no pre-release card features. A real card-strength model cannot be improved without joining the forecast feature table.",
      "folds":folds
    }
    (a.out_dir/"fin_blind_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    pd.DataFrame(folds).to_csv(a.out_dir/"fin_blind_folds.csv",index=False)
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
