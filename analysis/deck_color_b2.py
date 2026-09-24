#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
PAIRS=["WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"]
ORDER="WUBRG"
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}

def card_oof(d):
    nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
    txt=d["oracle_text"].fillna("")+" TYPE "+d["type_line"].fillna("")
    pred=np.zeros(len(d))
    for hold in sorted(DEV):
        tr=d["set"].str.upper()!=hold; te=~tr
        tree=make_pipeline(SimpleImputer(strategy="median"),
            ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
        tree.fit(d.loc[tr,nums],d.loc[tr,"actual_gih"])
        pt=tree.predict(d.loc[te,nums])
        text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
        text.fit(txt[tr],d.loc[tr,"actual_gih"])
        px=text.predict(txt[te])
        raw=.7*pt+.3*px
        center=float(d.loc[tr,"actual_gih"].mean())
        pred[te]=center+1.25*(raw-center)
    return pred

def eligible(g,p):
    m=(g["rarity_ord"].isin([0,1])) & (g["n_colors"]>0)
    for c in ORDER:
        if c not in p: m &= (g[f"color_{c}"]==0)
    return m

def pair_features(d):
    rows=[]
    for s,g in d.groupby("set"):
        for p in PAIRS:
            x=g.loc[eligible(g,p)].copy()
            vals=np.sort(x["pred_gih_oof"].to_numpy(float))[::-1]
            if len(vals)<20: raise RuntimeError(f"{s} {p}: only {len(vals)} eligible C/U cards")
            gold=x[x["n_colors"]==2]
            gold_excess=0.0 if gold.empty else float(gold["pred_gih_oof"].mean()-x["pred_gih_oof"].mean())
            rows.append({
                "set":s,"pair":p,
                "q_mean":float(vals.mean()),
                "q_top10":float(vals[:10].mean()),
                "q_depth10":float(vals[10:20].mean()),
                "gold_q_excess":gold_excess,
                "interaction_density":float(x["interaction"].fillna(0).mean()),
                "cheap_creature_density":float(((x["type_creature"]==1)&(x["mv"]<=3)).mean()),
                "card_adv_density":float(x["card_advantage"].fillna(0).mean()),
                "n_cards":int(len(x)),
            })
    q=pd.DataFrame(rows)
    features=["q_mean","q_top10","q_depth10","gold_q_excess","interaction_density","cheap_creature_density","card_adv_density"]
    for c in features:
        q[c+"_c"]=q[c]-q.groupby("set")[c].transform("mean")
    return q

BUNDLES={
    "B1_mean":["q_mean_c"],
    "B2_quality_shape":["q_mean_c","q_top10_c","q_depth10_c"],
    "B2_plus_gold":["q_mean_c","q_top10_c","q_depth10_c","gold_q_excess_c"],
    "B2_plus_roles":["q_mean_c","q_top10_c","q_depth10_c","gold_q_excess_c","interaction_density_c","cheap_creature_density_c","card_adv_density_c"],
}
ALPHAS=[0.1,1.0,10.0,100.0]

def fit_predict(train,test,features,alpha):
    m=make_pipeline(StandardScaler(),Ridge(alpha=alpha))
    m.fit(train[features],train["actual_delta"])
    p=m.predict(test[features])
    return p-p.mean()

def inner_score(train,bundle,alpha):
    maes=[]; sps=[]
    for hold in sorted(train["set"].unique()):
        tr=train[train["set"]!=hold]; te=train[train["set"]==hold]
        p=fit_predict(tr,te,BUNDLES[bundle],alpha)
        maes.append(np.mean(np.abs(te["actual_delta"].to_numpy()-p)))
        sps.append(spearmanr(te["actual_delta"],p).statistic)
    return float(np.mean(maes)),float(np.nanmean(sps))

def summarize(z,pred,delta):
    folds=[]
    for s,g in z.assign(pred=pred,pdelta=delta).groupby("set"):
        folds.append({
            "set":s,
            "mae_pp":float(np.mean(np.abs(g.actual_wr-g.pred))*100),
            "delta_mae_pp":float(np.mean(np.abs(g.actual_delta-g.pdelta))*100),
            "spearman":float(spearmanr(g.actual_wr,g.pred).statistic),
            "top2_recall":float(len(set(np.argsort(g.actual_wr.to_numpy())[-2:])&set(np.argsort(g.pred.to_numpy())[-2:]))/2),
            "bottom2_recall":float(len(set(np.argsort(g.actual_wr.to_numpy())[:2])&set(np.argsort(g.pred.to_numpy())[:2]))/2),
        })
    err=np.abs(z.actual_wr.to_numpy()-pred)
    return {
        "mae_pp":float(err.mean()*100),
        "delta_mae_pp":float(np.mean(np.abs(z.actual_delta.to_numpy()-delta))*100),
        "mean_set_spearman":float(np.mean([x["spearman"] for x in folds])),
        "mean_top2_recall":float(np.mean([x["top2_recall"] for x in folds])),
        "mean_bottom2_recall":float(np.mean([x["bottom2_recall"] for x in folds])),
        "game_weighted_mae_pp":float(np.average(err,weights=z.games)*100),
        "folds":folds,
    }

def main():
    feature_path=Path(sys.argv[1])
    actual_path=Path(sys.argv[2])
    out=Path(sys.argv[3] if len(sys.argv)>3 else "model_out_b2")
    out.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(feature_path)
    if "FIN" in set(d["set"].str.upper()) or set(d["set"].str.upper())!=DEV: raise SystemExit("FIN contamination / set mismatch")
    actual=pd.read_csv(actual_path)
    if "FIN" in set(actual["set"].str.upper()) or set(actual["set"].str.upper())!=DEV: raise SystemExit("FIN contamination / actual set mismatch")

    d["pred_gih_oof"]=card_oof(d)
    keep=["set","name","pred_gih_oof","rarity_ord","n_colors","mv","type_creature","interaction","card_advantage"]+[f"color_{c}" for c in ORDER]
    d[keep].to_csv(out/"card_gih_oof_for_deck_color.csv",index=False)
    pf=pair_features(d)
    pf.to_csv(out/"deck_color_b2_features.csv",index=False)

    z=actual.merge(pf,on=["set","pair"],how="inner")
    if len(z)!=220: raise SystemExit(f"expected 220 rows got {len(z)}")
    z["actual_set_mean"]=z.groupby("set")["actual_wr"].transform("mean")
    z["actual_delta"]=z["actual_wr"]-z["actual_set_mean"]

    pred=np.zeros(len(z)); delta=np.zeros(len(z)); selected={}
    for hold in sorted(DEV):
        tr=z[z["set"]!=hold].copy(); te=z[z["set"]==hold].copy()
        candidates=[]
        for b in BUNDLES:
            for a in ALPHAS:
                mae,sp=inner_score(tr,b,a)
                candidates.append((mae,-sp,b,a))
        candidates.sort()
        _,_,b,a=candidates[0]
        dd=fit_predict(tr,te,BUNDLES[b],a)
        mu=float(tr.groupby("set")["actual_wr"].mean().mean())
        idx=z["set"]==hold
        delta[idx]=dd; pred[idx]=mu+dd
        selected[hold]={"bundle":b,"alpha":a,"inner_delta_mae_pp":float(candidates[0][0]*100),"inner_spearman":float(-candidates[0][1]),"environment_mean":mu}

    z["b2_nested_pred_wr"]=pred; z["b2_nested_pred_delta"]=delta
    z.to_csv(out/"deck_color_b2_predictions.csv",index=False)
    report={"fin_used":False,"selection":"outer LOSO; bundle and Ridge alpha chosen by inner set-LOSO using delta MAE, Spearman tie-break",
            "bundles":BUNDLES,"alphas":ALPHAS,"selected":selected,"B2_nested":summarize(z,pred,delta)}
    (out/"deck_color_b2_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("B2_REPORT",json.dumps(report["B2_nested"]))
    print("B2_SELECTION",json.dumps(selected))
if __name__=="__main__": main()
