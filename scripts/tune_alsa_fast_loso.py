#!/usr/bin/env python3
"""Focused FIN-blind ALSA sweep on cached 22-set development data."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.neighbors import NearestNeighbors
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
    X0=pd.concat([d[base].reset_index(drop=True),rarity.reset_index(drop=True)],axis=1)
    # Historical-card analog ALSA: computed strictly inside each LOSO fold.
    # Similarity uses only pre-release numeric/card metadata; the held-out set never enters the neighbor DB.
    analog=np.full(len(d),np.nan)
    analog_med=np.full(len(d),np.nan)
    simcols=[c for c in base if c not in {"year"}]
    A=SimpleImputer(strategy="median").fit_transform(d[simcols])
    scale=np.nanstd(A,axis=0); scale[scale==0]=1; A=A/scale
    for hold in sorted(d["set"].unique()):
      tr=(d["set"]!=hold).to_numpy(); te=~tr
      nn=NearestNeighbors(n_neighbors=min(12,int(tr.sum())),metric="euclidean").fit(A[tr])
      dist,ix=nn.kneighbors(A[te]); vals=d.loc[tr,"actual_alsa"].to_numpy()[ix]
      w=1/(dist+0.15); analog[te]=(vals*w).sum(axis=1)/w.sum(axis=1); analog_med[te]=np.median(vals,axis=1)
    # Analog experiment did not improve LOSO; keep it computed for audit but do not feed it to the next model.
    X=X0
    # ALSA-specific perceived-strength semantics generated directly from oracle/type text.
    txt=d.get("oracle_text",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    typ=d.get("type_line",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    semdf=pd.DataFrame(index=d.index)
    semdf["alsa_sem_removal"]=txt.str.contains(r"destroy target|exile target|deals? \\d+ damage to target|target creature gets -").astype(float)
    semdf["alsa_sem_draw"]=txt.str.contains(r"draw (a|one|two|three|\\d+) cards?").astype(float)
    semdf["alsa_sem_evasion"]=(txt.str.contains(r"flying|menace|trample|can't be blocked")|typ.str.contains("vehicle")).astype(float)
    semdf["alsa_sem_repeatable"]=txt.str.contains(r"at the beginning of|whenever|: draw|: create|: target").astype(float)
    semdf["alsa_sem_sweeper"]=txt.str.contains(r"all creatures|each creature|all other creatures").astype(float)
    semdf["alsa_sem_dependency"]=txt.str.contains(r"if you control|for each|as long as|another .* you control|cards? in your graveyard").astype(float)
    semdf["alsa_sem_narrow"]=txt.str.contains(r"artifact or enchantment|nonbasic land|creature with flying|from a graveyard").astype(float)
    semdf["alsa_sem_creature"]=typ.str.contains("creature").astype(float)
    if int(semdf.to_numpy().sum())==0: raise SystemExit("ALSA semantic generation produced zero active values")
    X=pd.concat([X0,semdf.reset_index(drop=True)],axis=1)
    sem=list(semdf.columns); added=[]
    for c in sem:
      for r in rarity.columns:
        n=f"{c}_x_{r}"; X[n]=X[c].to_numpy()*rarity[r].to_numpy(); added.append(n)
    if not added: raise SystemExit("ALSA semantic rarity interactions produced zero columns")
    print("ALSA_SEMANTIC_AUDIT",json.dumps({"semantic_columns":sem,"interaction_count":len(added),"active_values":int(semdf.to_numpy().sum())}))
    yy=d.actual_alsa.to_numpy(float); results=[]
    for name,kw in candidates():
      p=np.full(len(d),np.nan); floors=np.full(len(d),np.nan)
      for hold in sorted(d["set"].unique()):
        tr=(d["set"]!=hold).to_numpy(); te=~tr
        m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingRegressor(**kw))
        m.fit(X.loc[tr],d.loc[tr,"actual_alsa"]); p[te]=m.predict(X.loc[te]); floors[te]=float(d.loc[tr,"actual_alsa"].min())
      ok=np.isfinite(p)&np.isfinite(yy)
      mae=float(np.mean(np.abs(p[ok]-yy[ok]))); sp=float(spearmanr(yy[ok],p[ok]).statistic)
      per={s:float(np.mean(np.abs(p[(d["set"]==s)&ok]-yy[(d["set"]==s)&ok]))) for s in sorted(d["set"].unique())}
      rmae={}
      if "rarity" in d.columns:
        for r in sorted(d["rarity"].dropna().astype(str).unique()):
          z=(d["rarity"].astype(str)==r).to_numpy()&ok
          if z.any(): rmae[r]=float(np.mean(np.abs(p[z]-yy[z])))
      z={"name":name,"mae":mae,"spearman":sp,"pred_min":float(p[ok].min()),"pred_max":float(p[ok].max()),"pred_le_1":int((p[ok]<=1).sum()),"pred_lt_1_05":int((p[ok]<1.05).sum()),"rarity_mae":rmae,"set_mae":per}
      if z["pred_min"]>1.0:
        z["variant"]="raw"; results.append(z); print("ALSA_SWEEP",name,"raw MAE",mae,"SPEARMAN",sp,"MIN",z["pred_min"])
      # Fold-local empirical floor: learned only from each training fold, never FIN or held-out set.
      pf=np.maximum(p,floors+1e-6); okf=np.isfinite(pf)&np.isfinite(yy)
      zf=dict(z); zf.update(name=name+"_foldfloor",variant="foldfloor",mae=float(np.mean(np.abs(pf[okf]-yy[okf]))),spearman=float(spearmanr(yy[okf],pf[okf]).statistic),pred_min=float(pf[okf].min()),pred_max=float(pf[okf].max()),pred_le_1=int((pf[okf]<=1).sum()),pred_lt_1_05=int((pf[okf]<1.05).sum()))
      if zf["pred_min"]>1.0:
        results.append(zf); print("ALSA_SWEEP",zf["name"],"MAE",zf["mae"],"SPEARMAN",zf["spearman"],"MIN",zf["pred_min"])
    if not results: raise SystemExit("No candidate satisfies mandatory pred_min > 1.0")
    results.sort(key=lambda z:(z["mae"],-z["spearman"]))
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps({"fin_used":False,"n":len(d),"results":results},indent=2),encoding="utf-8")
    print("FIN_USED=false"); print("ALSA_BEST",json.dumps(results[0]))
if __name__=="__main__": main()
