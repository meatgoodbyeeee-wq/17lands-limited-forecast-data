#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.preprocessing import StandardScaler

DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
PAIRS=["WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"]; ORDER="WUBRG"
DROP={"actual_gih","gih_wr","gih_wr_pct","gih_games","gih_wins","actual_alsa","collector_number"}
NONNUM={"set","name","oracle_text","type_line","window_start","window_end","rarity"}

def alsa_cols(d):
    return [c for c in d.columns if c not in DROP|NONNUM and pd.api.types.is_numeric_dtype(d[c])]

def adopted_X(d):
    base=alsa_cols(d)
    rarity=pd.get_dummies(d.get("rarity",pd.Series("unknown",index=d.index)).fillna("unknown").astype(str),prefix="rarity",dtype=float)
    X0=pd.concat([d[base].reset_index(drop=True),rarity.reset_index(drop=True)],axis=1)
    txt=d.get("oracle_text",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    typ=d.get("type_line",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    sem=pd.DataFrame(index=d.index)
    sem["alsa_sem_removal"]=txt.str.contains(r"destroy target|exile target|target creature gets -").astype(float)
    sem["alsa_sem_draw"]=txt.str.contains(r"draw (a|one|two|three|\d+) cards?").astype(float)
    sem["alsa_sem_evasion"]=(txt.str.contains(r"flying|menace|trample|can't be blocked")|typ.str.contains("vehicle")).astype(float)
    sem["alsa_sem_repeatable"]=txt.str.contains(r"at the beginning of|whenever|: draw|: create|: target").astype(float)
    sem["alsa_sem_sweeper"]=txt.str.contains(r"all creatures|each creature|all other creatures").astype(float)
    sem["alsa_sem_dependency"]=txt.str.contains(r"if you control|for each|as long as|another .* you control|cards? in your graveyard").astype(float)
    sem["alsa_sem_narrow"]=txt.str.contains(r"artifact or enchantment|nonbasic land|creature with flying|from a graveyard").astype(float)
    sem["alsa_sem_creature"]=typ.str.contains("creature").astype(float)
    X=pd.concat([X0,sem.reset_index(drop=True)],axis=1)
    for c in sem:
        for r in rarity.columns:
            X[f"{c}_x_{r}"]=X[c].to_numpy()*rarity[r].to_numpy()
    repeat=["alsa_sem_repeatable"]+[c for c in X.columns if c.startswith("alsa_sem_repeatable_x_")]
    X=X.drop(columns=repeat)
    X["alsa_pair_removal_draw"]=sem["alsa_sem_removal"].to_numpy()*sem["alsa_sem_draw"].to_numpy()
    X["alsa_sem_mana_fix"]=txt.str.contains(r"add one mana of any color|search your library for (a|up to one|one) basic land|basic land card").astype(float).to_numpy()
    return X

def pmask(g,p):
    m=(g.rarity_ord.isin([0,1]))&(g.n_colors>0)
    for c in ORDER:
        if c not in p: m &= g[f"color_{c}"].eq(0)
    return m

def fit(z,features,ridge=False):
    pred=np.zeros(len(z)); delta=np.zeros(len(z))
    for hold in sorted(DEV):
        tr=z.set.ne(hold); te=~tr
        mu=float(z.loc[tr].groupby("set").actual_wr.mean().mean())
        m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)) if ridge else LinearRegression()
        m.fit(z.loc[tr,features],z.loc[tr,"actual_delta"])
        dd=m.predict(z.loc[te,features]); dd=dd-dd.mean()
        delta[te]=dd; pred[te]=mu+dd
    return pred,delta

def metrics(z,p,d):
    folds=[]
    for s,g in z.assign(pred=p,pdelta=d).groupby("set"):
        folds.append({"set":s,"mae_pp":float(np.mean(abs(g.actual_wr-g.pred))*100),
          "delta_mae_pp":float(np.mean(abs(g.actual_delta-g.pdelta))*100),
          "spearman":float(spearmanr(g.actual_wr,g.pred).statistic)})
    err=abs(z.actual_wr.to_numpy()-p)
    return {"mae_pp":float(err.mean()*100),"delta_mae_pp":float(np.mean(abs(z.actual_delta.to_numpy()-d))*100),
      "mean_set_spearman":float(np.nanmean([x["spearman"] for x in folds])),
      "game_weighted_mae_pp":float(np.average(err,weights=z.games)*100),"folds":folds}

def main():
    f=pd.read_csv(sys.argv[1]); y=pd.read_csv(sys.argv[2]); gih=pd.read_csv(sys.argv[3]); actual=pd.read_csv(sys.argv[4]); out=Path(sys.argv[5]); out.mkdir(parents=True,exist_ok=True)
    for label,x in [("features",f),("alsa",y),("gih",gih),("color",actual)]:
        sets=set(x.set.astype(str).str.upper())
        if "FIN" in sets or sets!=DEV: raise SystemExit(f"{label}: FIN contamination/set mismatch")
    d=f.merge(y,on=["set","name"],how="inner")
    X=adopted_X(d); yy=d.actual_alsa.to_numpy(float); pa=np.full(len(d),np.nan)
    for hold in sorted(DEV):
        tr=d.set.ne(hold).to_numpy(); te=~tr
        m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingRegressor(loss="squared_error",max_iter=250,learning_rate=.06,l2_regularization=2,random_state=20260923))
        m.fit(X.loc[tr],d.loc[tr,"actual_alsa"])
        floor=float(d.loc[tr,"actual_alsa"].min())+1e-6
        pa[te]=np.maximum(m.predict(X.loc[te]),floor)
    amae=float(np.mean(abs(pa-yy))); asp=float(spearmanr(yy,pa).statistic)
    print("ALSA_REPRO",json.dumps({"mae":amae,"spearman":asp,"pred_min":float(pa.min())}))
    if abs(amae-0.8399666882842912)>1e-8 or abs(asp-0.8372004903709611)>1e-8:
        raise SystemExit("Adopted ALSA OOF did not reproduce exactly")
    d["pred_alsa_oof"]=pa
    d=d.merge(gih,on=["set","name"],how="left")
    if d.pred_gih_oof.isna().any(): raise SystemExit("Missing GIH OOF predictions")
    d[["set","name","pred_alsa_oof"]].to_csv(out/"deck_color_alsa_oof.csv",index=False)
    d["alsa_pct"]=d.groupby(["set","rarity_ord"]).pred_alsa_oof.rank(pct=True,method="average")

    rows=[]
    for s,g in d.groupby("set"):
        cu=(g.rarity_ord.isin([0,1]))&(g.n_colors>0); ref=float(g.loc[cu,"pred_gih_oof"].median())
        for p in PAIRS:
            h=g.loc[pmask(g,p)].copy(); excess=np.maximum(h.pred_gih_oof.to_numpy()-ref,0); ap=h.alsa_pct.to_numpy()
            common=h.rarity_ord.eq(0).to_numpy(); uncommon=h.rarity_ord.eq(1).to_numpy()
            aw=lambda m: float(np.mean(excess[m]*ap[m])) if m.any() else 0.0
            rows.append({"set":s,"pair":p,"gih_simple_mean":float(h.pred_gih_oof.mean()),
              "avail_good_all":aw(np.ones(len(h),dtype=bool)),"avail_good_common":aw(common),"avail_good_uncommon":aw(uncommon)})
    z=actual.merge(pd.DataFrame(rows),on=["set","pair"],how="inner")
    z["actual_set_mean"]=z.groupby("set").actual_wr.transform("mean"); z["actual_delta"]=z.actual_wr-z.actual_set_mean
    for c in ["gih_simple_mean","avail_good_all","avail_good_common","avail_good_uncommon"]:
        z[c+"_c"]=z[c]-z.groupby("set")[c].transform("mean")
    p1,d1=fit(z,["gih_simple_mean_c"],False)
    pa1,da1=fit(z,["gih_simple_mean_c","avail_good_all_c"],True)
    par,dar=fit(z,["gih_simple_mean_c","avail_good_common_c","avail_good_uncommon_c"],True)
    rep={"fin_used":False,"alsa_repro":{"mae":amae,"spearman":asp},"B1":metrics(z,p1,d1),"B4_ALL":metrics(z,pa1,da1),"B4_RARITY":metrics(z,par,dar)}
    for k in ["B4_ALL","B4_RARITY"]:
        rep[k]["vs_B1"]={"mae_pp_change":rep[k]["mae_pp"]-rep["B1"]["mae_pp"],"delta_mae_pp_change":rep[k]["delta_mae_pp"]-rep["B1"]["delta_mae_pp"],"spearman_change":rep[k]["mean_set_spearman"]-rep["B1"]["mean_set_spearman"]}
    z.assign(b1_pred=p1,b4_all_pred=pa1,b4_rarity_pred=par).to_csv(out/"deck_color_alsa_validation.csv",index=False)
    (out/"deck_color_alsa_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("B4_SUMMARY",json.dumps({k:{m:rep[k][m] for m in ["mae_pp","delta_mae_pp","mean_set_spearman","game_weighted_mae_pp"]} for k in ["B1","B4_ALL","B4_RARITY"]}))
    print("B4_VS_B1",json.dumps({k:rep[k]["vs_B1"] for k in ["B4_ALL","B4_RARITY"]}))
if __name__=="__main__": main()
