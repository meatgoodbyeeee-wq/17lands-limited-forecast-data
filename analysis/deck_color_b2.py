#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
PAIRS=["WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"]; ORDER="WUBRG"
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
B2_GIH=["gih_simple_mean","gih_top4_mean","gih_depth"]
B2_STRUCT=B2_GIH+["early_creature_count","clean_interaction_count","clean_interaction_quality","card_advantage_count","card_advantage_quality"]

def card_oof(d):
    nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
    txt=d.oracle_text.fillna("")+" TYPE "+d.type_line.fillna("")
    pred=np.zeros(len(d))
    for hold in sorted(DEV):
        tr=d.set.str.upper()!=hold; te=~tr
        tree=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
        tree.fit(d.loc[tr,nums],d.loc[tr,"actual_gih"])
        text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
        text.fit(txt[tr],d.loc[tr,"actual_gih"])
        raw=.7*tree.predict(d.loc[te,nums])+.3*text.predict(txt[te])
        center=float(d.loc[tr,"actual_gih"].mean())
        pred[te]=center+1.25*(raw-center)
    return pred

def pmask(g,p):
    m=(g.rarity_ord.isin([0,1]))&(g.n_colors>0)
    for c in ORDER:
        if c not in p: m &= g[f"color_{c}"].eq(0)
    return m

def pair_features(d):
    rows=[]
    for s,g in d.groupby("set"):
        cu=(g.rarity_ord.isin([0,1]))&(g.n_colors>0)
        ref=float(g.loc[cu,"pred_gih_oof"].median())
        for p in PAIRS:
            h=g.loc[pmask(g,p)].copy()
            vals=h.pred_gih_oof.astype(float).sort_values(ascending=False)
            clean=h.clean_interaction.gt(0); ca=h.card_advantage.gt(0)
            early=h.type_creature.gt(0)&h.mv.between(2,3)
            rows.append({
                "set":s,"pair":p,"n_cards":len(h),
                "gih_simple_mean":float(vals.mean()),
                "gih_top4_mean":float(vals.head(4).mean()),
                "gih_depth":float((vals>ref).mean()),
                "early_creature_count":int(early.sum()),
                "clean_interaction_count":int(clean.sum()),
                "clean_interaction_quality":float(h.loc[clean,"pred_gih_oof"].mean()) if clean.any() else ref,
                "card_advantage_count":int(ca.sum()),
                "card_advantage_quality":float(h.loc[ca,"pred_gih_oof"].mean()) if ca.any() else ref,
            })
    return pd.DataFrame(rows)

def center(z,cols):
    out=[]
    for c in cols:
        cc=c+"_c"; z[cc]=z[c]-z.groupby("set")[c].transform("mean"); out.append(cc)
    return out

def fit_loso(z,features,ridge=False):
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
        sp=spearmanr(g.actual_wr,g.pred).statistic
        folds.append({"set":s,"mae_pp":float(np.mean(abs(g.actual_wr-g.pred))*100),
          "delta_mae_pp":float(np.mean(abs(g.actual_delta-g.pdelta))*100),"spearman":float(sp),
          "top2_recall":len(set(np.argsort(g.actual_wr.to_numpy())[-2:])&set(np.argsort(g.pred.to_numpy())[-2:]))/2,
          "bottom2_recall":len(set(np.argsort(g.actual_wr.to_numpy())[:2])&set(np.argsort(g.pred.to_numpy())[:2]))/2})
    err=abs(z.actual_wr.to_numpy()-p)
    return {"mae_pp":float(err.mean()*100),"delta_mae_pp":float(np.mean(abs(z.actual_delta.to_numpy()-d))*100),
      "mean_set_spearman":float(np.nanmean([x["spearman"] for x in folds])),
      "mean_top2_recall":float(np.mean([x["top2_recall"] for x in folds])),
      "mean_bottom2_recall":float(np.mean([x["bottom2_recall"] for x in folds])),
      "game_weighted_mae_pp":float(np.average(err,weights=z.games)*100),"folds":folds}

def main():
    feat,actualp,out=Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]); out.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(feat); actual=pd.read_csv(actualp)
    for label,x in [("features",d),("actuals",actual)]:
        sets=set(x.set.str.upper())
        if "FIN" in sets or sets!=DEV: raise SystemExit(f"{label}: FIN contamination/set mismatch {sorted(sets)}")
    d["pred_gih_oof"]=card_oof(d)
    d[["set","name","pred_gih_oof"]].to_csv(out/"card_gih_oof_for_deck_color.csv",index=False)
    z=actual.merge(pair_features(d),on=["set","pair"])
    if len(z)!=220: raise SystemExit(f"expected 220 rows got {len(z)}")
    z["actual_set_mean"]=z.groupby("set").actual_wr.transform("mean"); z["actual_delta"]=z.actual_wr-z.actual_set_mean
    f1=center(z,["gih_simple_mean"]); f2g=f1+center(z,[x for x in B2_GIH if x!="gih_simple_mean"])
    f2s=f2g+center(z,[x for x in B2_STRUCT if x not in B2_GIH])
    p1,d1=fit_loso(z,f1,False); pg,dg=fit_loso(z,f2g,True); ps,ds=fit_loso(z,f2s,True)
    z["b1_pred_wr"]=p1; z["b2_gih_pred_wr"]=pg; z["b2_struct_pred_wr"]=ps
    z.to_csv(out/"deck_color_b2_predictions.csv",index=False)
    rep={"fin_used":False,"ridge_alpha_fixed":10.0,"features":{"B1":f1,"B2_GIH":f2g,"B2_STRUCT":f2s},
         "B1":metrics(z,p1,d1),"B2_GIH":metrics(z,pg,dg),"B2_STRUCT":metrics(z,ps,ds)}
    for k in ["B2_GIH","B2_STRUCT"]:
        rep[k]["vs_B1"]={"mae_pp_change":rep[k]["mae_pp"]-rep["B1"]["mae_pp"],
          "delta_mae_pp_change":rep[k]["delta_mae_pp"]-rep["B1"]["delta_mae_pp"],
          "spearman_change":rep[k]["mean_set_spearman"]-rep["B1"]["mean_set_spearman"],
          "sets_mae_better":sum(a["mae_pp"]<b["mae_pp"] for a,b in zip(rep[k]["folds"],rep["B1"]["folds"])),
          "sets_delta_better":sum(a["delta_mae_pp"]<b["delta_mae_pp"] for a,b in zip(rep[k]["folds"],rep["B1"]["folds"]))}
    (out/"deck_color_b2_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("B2_SUMMARY",json.dumps({k:{m:rep[k][m] for m in ["mae_pp","delta_mae_pp","mean_set_spearman","mean_top2_recall","mean_bottom2_recall","game_weighted_mae_pp"]} for k in ["B1","B2_GIH","B2_STRUCT"]}))
    print("B2_VS_B1",json.dumps({k:rep[k]["vs_B1"] for k in ["B2_GIH","B2_STRUCT"]}))
if __name__=="__main__": main()
