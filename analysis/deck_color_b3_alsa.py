#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
PAIRS=["WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"]
ORDER="WUBRG"
ALSA_DROP={"actual_gih","gih_wr","gih_wr_pct","gih_games","gih_wins","actual_alsa","collector_number"}

def alsa_matrix(f,y):
    d=f.merge(y,on=["set","name"],how="inner")
    base=[c for c in d.columns if c not in ALSA_DROP|{"set","name","oracle_text","type_line","window_start","window_end","rarity"} and pd.api.types.is_numeric_dtype(d[c])]
    rarity=pd.get_dummies(d.get("rarity",pd.Series("unknown",index=d.index)).fillna("unknown").astype(str),prefix="rarity",dtype=float)
    X0=pd.concat([d[base].reset_index(drop=True),rarity.reset_index(drop=True)],axis=1)
    txt=d.get("oracle_text",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    typ=d.get("type_line",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    sem=pd.DataFrame(index=d.index)
    sem["alsa_sem_removal"]=txt.str.contains(r"destroy target|exile target|target creature gets -").astype(float)
    sem["alsa_sem_draw"]=txt.str.contains(r"draw (a|one|two|three|\\d+) cards?").astype(float)
    sem["alsa_sem_evasion"]=(txt.str.contains(r"flying|menace|trample|can't be blocked")|typ.str.contains("vehicle")).astype(float)
    sem["alsa_sem_repeatable"]=txt.str.contains(r"at the beginning of|whenever|: draw|: create|: target").astype(float)
    sem["alsa_sem_sweeper"]=txt.str.contains(r"all creatures|each creature|all other creatures").astype(float)
    sem["alsa_sem_dependency"]=txt.str.contains(r"if you control|for each|as long as|another .* you control|cards? in your graveyard").astype(float)
    sem["alsa_sem_narrow"]=txt.str.contains(r"artifact or enchantment|nonbasic land|creature with flying|from a graveyard").astype(float)
    sem["alsa_sem_creature"]=typ.str.contains("creature").astype(float)
    X=pd.concat([X0,sem.reset_index(drop=True)],axis=1)
    for c in sem.columns:
        for r in rarity.columns:
            X[f"{c}_x_{r}"]=X[c].to_numpy()*rarity[r].to_numpy()
    repeat=["alsa_sem_repeatable"]+[c for c in X.columns if c.startswith("alsa_sem_repeatable_x_")]
    X=X.drop(columns=repeat)
    X["alsa_pair_removal_draw"]=sem["alsa_sem_removal"].to_numpy()*sem["alsa_sem_draw"].to_numpy()
    X["alsa_sem_mana_fix"]=txt.str.contains(r"add one mana of any color|search your library for (a|up to one|one) basic land|basic land card").astype(float).to_numpy()
    return d,X

def alsa_oof(f,y):
    d,X=alsa_matrix(f,y)
    p=np.full(len(d),np.nan)
    kw=dict(loss="squared_error",max_iter=250,learning_rate=.06,l2_regularization=2,random_state=20260923)
    for hold in sorted(d["set"].unique()):
        tr=(d["set"]!=hold).to_numpy(); te=~tr
        m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingRegressor(**kw))
        m.fit(X.loc[tr],d.loc[tr,"actual_alsa"])
        ph=m.predict(X.loc[te])
        floor=float(d.loc[tr,"actual_alsa"].min())+1e-6
        p[te]=np.maximum(ph,floor)
    return d[["set","name","actual_alsa"]].assign(pred_alsa_oof=p)

def pair_features(cards):
    cards=cards.copy()
    cards["alsa_pct"]=cards.groupby(["set","rarity_ord"])["pred_alsa_oof"].rank(pct=True,method="average")
    cards["gih_rarity_base"]=cards.groupby(["set","rarity_ord"])["pred_gih_oof"].transform("median")
    cards["positive_quality"]=(cards["pred_gih_oof"]-cards["gih_rarity_base"]).clip(lower=0)
    cards["available_quality"]=cards["positive_quality"]*cards["alsa_pct"]
    rows=[]
    for s,g in cards.groupby("set"):
        for p in PAIRS:
            m=g["rarity_ord"].isin([0,1]) & (g["n_colors"]>0)
            for c in ORDER:
                if c not in p: m &= (g[f"color_{c}"]==0)
            x=g.loc[m]
            if x.empty: raise RuntimeError(f"{s} {p}: no eligible cards")
            cm=x[x["rarity_ord"]==0]; un=x[x["rarity_ord"]==1]
            rows.append({
                "set":s,"pair":p,
                "q_mean":float(x["pred_gih_oof"].mean()),
                "avail_all":float(x["available_quality"].mean()),
                "avail_common":float(cm["available_quality"].mean()) if len(cm) else 0.0,
                "avail_uncommon":float(un["available_quality"].mean()) if len(un) else 0.0,
                "mean_alsa":float(x["pred_alsa_oof"].mean()),
                "n_cards":int(len(x))
            })
    q=pd.DataFrame(rows)
    for c in ["q_mean","avail_all","avail_common","avail_uncommon","mean_alsa"]:
        q[c+"_c"]=q[c]-q.groupby("set")[c].transform("mean")
    return q

BUNDLES={
    "B1_mean":["q_mean_c"],
    "B3_avail_all":["q_mean_c","avail_all_c"],
    "B3_avail_rarity":["q_mean_c","avail_common_c","avail_uncommon_c"],
}
ALPHAS=[0.1,1.0,10.0,100.0]

def fit_predict(train,test,features,alpha):
    m=make_pipeline(StandardScaler(),Ridge(alpha=alpha))
    m.fit(train[features],train["actual_delta"])
    p=m.predict(test[features])
    return p-p.mean()

def inner_score(train,b,a):
    maes=[]; sps=[]
    for hold in sorted(train["set"].unique()):
        tr=train[train["set"]!=hold]; te=train[train["set"]==hold]
        p=fit_predict(tr,te,BUNDLES[b],a)
        maes.append(float(np.mean(np.abs(te.actual_delta.to_numpy()-p))))
        sps.append(float(spearmanr(te.actual_delta,p).statistic))
    return float(np.mean(maes)),float(np.nanmean(sps))

def summarize(z,pred,delta):
    fs=[]
    for s,g in z.assign(pred=pred,pdelta=delta).groupby("set"):
        yy=g.actual_wr.to_numpy(); pp=g.pred.to_numpy()
        fs.append({"set":s,
          "mae_pp":float(np.mean(np.abs(yy-pp))*100),
          "delta_mae_pp":float(np.mean(np.abs(g.actual_delta-g.pdelta))*100),
          "spearman":float(spearmanr(yy,pp).statistic),
          "top2_recall":float(len(set(np.argsort(yy)[-2:])&set(np.argsort(pp)[-2:]))/2),
          "bottom2_recall":float(len(set(np.argsort(yy)[:2])&set(np.argsort(pp)[:2]))/2)})
    err=np.abs(z.actual_wr.to_numpy()-pred)
    return {"mae_pp":float(err.mean()*100),
      "delta_mae_pp":float(np.mean(np.abs(z.actual_delta.to_numpy()-delta))*100),
      "mean_set_spearman":float(np.mean([x["spearman"] for x in fs])),
      "mean_top2_recall":float(np.mean([x["top2_recall"] for x in fs])),
      "mean_bottom2_recall":float(np.mean([x["bottom2_recall"] for x in fs])),
      "game_weighted_mae_pp":float(np.average(err,weights=z.games)*100),
      "folds":fs}

def main():
    feature_path=Path(sys.argv[1]); alsa_path=Path(sys.argv[2]); gih_oof_path=Path(sys.argv[3]); actual_path=Path(sys.argv[4]); out=Path(sys.argv[5])
    out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_path); y=pd.read_csv(alsa_path); gih=pd.read_csv(gih_oof_path); actual=pd.read_csv(actual_path)
    for name,d in [("features",f),("alsa",y),("gih",gih),("actual",actual)]:
        sets=set(d["set"].astype(str).str.upper())
        if "FIN" in sets or sets!=DEV: raise SystemExit(f"{name}: FIN contamination/set mismatch {sorted(sets)}")
    ao=alsa_oof(f,y)
    ao.to_csv(out/"card_alsa_oof_for_deck_color.csv",index=False)
    cards=gih.merge(ao[["set","name","pred_alsa_oof"]],on=["set","name"],how="inner")
    pf=pair_features(cards); pf.to_csv(out/"deck_color_b3_alsa_features.csv",index=False)
    z=actual.merge(pf,on=["set","pair"],how="inner")
    if len(z)!=220: raise SystemExit(f"expected 220 rows got {len(z)}")
    z["actual_set_mean"]=z.groupby("set")["actual_wr"].transform("mean")
    z["actual_delta"]=z["actual_wr"]-z["actual_set_mean"]
    pred=np.zeros(len(z)); delta=np.zeros(len(z)); selected={}
    for hold in sorted(DEV):
        tr=z[z["set"]!=hold].copy(); te=z[z["set"]==hold].copy()
        cand=[]
        for b in BUNDLES:
            for a in ALPHAS:
                mae,sp=inner_score(tr,b,a); cand.append((mae,-sp,b,a))
        cand.sort(); _,_,b,a=cand[0]
        dd=fit_predict(tr,te,BUNDLES[b],a)
        mu=float(tr.groupby("set")["actual_wr"].mean().mean())
        idx=z["set"]==hold; delta[idx]=dd; pred[idx]=mu+dd
        selected[hold]={"bundle":b,"alpha":a,"inner_delta_mae_pp":float(cand[0][0]*100),"inner_spearman":float(-cand[0][1]),"environment_mean":mu}
    z["b3_pred_wr"]=pred; z["b3_pred_delta"]=delta
    z.to_csv(out/"deck_color_b3_alsa_predictions.csv",index=False)
    report={"fin_used":False,
      "alsa_model":"current adopted FIN-blind HGB: squared_error, lr=.06, l2=2, max_iter=250, fold-local floor",
      "availability":"positive predicted GIH excess within set/rarity multiplied by predicted ALSA percentile; weak late cards contribute zero",
      "selection":"outer LOSO; bundle/alpha selected by inner set-LOSO",
      "bundles":BUNDLES,"selected":selected,"B3_nested":summarize(z,pred,delta)}
    (out/"deck_color_b3_alsa_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("B3_REPORT",json.dumps(report["B3_nested"]))
    print("B3_SELECTION",json.dumps(selected))
if __name__=="__main__": main()
