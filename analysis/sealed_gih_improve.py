#!/usr/bin/env python3
import sys,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline

SETS=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number",
      "sealed_gih","sealed_gih_count","sealed_gih_wins"}
RMAP={0:"C",1:"U",2:"R",3:"M"}

def nums(d,extra=False):
    base=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
    if not extra:
        base=[c for c in base if c!="pred_gih_oof"]
    return base

def fit_predict(train,test,target_col,features,weight_mode="none",centered=False):
    y=train[target_col].to_numpy(float)
    if centered:
        means=train.groupby("set")[target_col].transform("mean").to_numpy(float)
        y=y-means
    w=None
    if weight_mode=="sqrt":
        w=np.sqrt(train.sealed_gih_count.to_numpy(float))
        w=w/np.mean(w)
    elif weight_mode=="log":
        w=np.log1p(train.sealed_gih_count.to_numpy(float))
        w=w/np.mean(w)

    imp=SimpleImputer(strategy="median")
    Xtr=imp.fit_transform(train[features]); Xte=imp.transform(test[features])
    tree=ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922)
    tree.fit(Xtr,y,sample_weight=w)
    pt=tree.predict(Xte)

    vect=TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True)
    txttr=train.oracle_text.fillna("")+" TYPE "+train.type_line.fillna("")
    txtte=test.oracle_text.fillna("")+" TYPE "+test.type_line.fillna("")
    A=vect.fit_transform(txttr); B=vect.transform(txtte)
    ridge=Ridge(alpha=10)
    ridge.fit(A,y,sample_weight=w)
    px=ridge.predict(B)
    raw=.7*pt+.3*px

    if centered:
        base=float(train.groupby("set")[target_col].mean().mean())
        return base+1.25*raw
    center=float(np.average(train[target_col],weights=w) if w is not None else train[target_col].mean())
    return center+1.25*(raw-center)

def oof(d,kind):
    pred=np.full(len(d),np.nan)
    base_features=nums(d,extra=False)
    draft_features=nums(d,extra=True)
    for hold in SETS:
        tr=d[d.set.ne(hold)];te=d[d.set.eq(hold)]
        if kind=="BASE":
            p=fit_predict(tr,te,"sealed_gih",base_features)
        elif kind=="WEIGHT_SQRT":
            p=fit_predict(tr,te,"sealed_gih",base_features,"sqrt")
        elif kind=="WEIGHT_LOG":
            p=fit_predict(tr,te,"sealed_gih",base_features,"log")
        elif kind=="CENTERED":
            p=fit_predict(tr,te,"sealed_gih",base_features,"none",True)
        elif kind=="CENTERED_WEIGHT":
            p=fit_predict(tr,te,"sealed_gih",base_features,"sqrt",True)
        elif kind=="DRAFT_AUX":
            p=fit_predict(tr,te,"sealed_gih",draft_features)
        elif kind=="DRAFT_AUX_WEIGHT":
            p=fit_predict(tr,te,"sealed_gih",draft_features,"sqrt")
        else: raise ValueError(kind)
        pred[te.index]=p
    return pred

def metrics(d,p):
    q=d.copy();q["pred"]=p;q["ae"]=abs(q.sealed_gih-q.pred)
    folds=[]
    for s,g in q.groupby("set"):
        folds.append({"set":s,"n":len(g),"mae_pp":float(g.ae.mean()*100),
          "weighted_mae_pp":float(np.average(g.ae,weights=np.sqrt(g.sealed_gih_count))*100),
          "spearman":float(spearmanr(g.sealed_gih,g.pred).statistic),
          "bias_pp":float((g.pred-g.sealed_gih).mean()*100)})
    rarity={}
    for r,g in q.groupby("rarity_ord"):
        rarity[RMAP.get(int(r),str(r))]={"n":len(g),"mae_pp":float(g.ae.mean()*100),
          "weighted_mae_pp":float(np.average(g.ae,weights=np.sqrt(g.sealed_gih_count))*100),
          "spearman":float(spearmanr(g.sealed_gih,g.pred).statistic)}
    thresholds={}
    for t in [30,100,300,1000,3000]:
        g=q[q.sealed_gih_count>=t]
        thresholds[str(t)]={"n":len(g),"mae_pp":float(g.ae.mean()*100),
          "spearman":float(spearmanr(g.sealed_gih,g.pred).statistic)}
    return {"mae_pp":float(q.ae.mean()*100),
      "sqrt_count_weighted_mae_pp":float(np.average(q.ae,weights=np.sqrt(q.sealed_gih_count))*100),
      "spearman":float(spearmanr(q.sealed_gih,q.pred).statistic),
      "macro_set_mae_pp":float(np.mean([x["mae_pp"] for x in folds])),
      "macro_set_spearman":float(np.mean([x["spearman"] for x in folds])),
      "mean_abs_set_bias_pp":float(np.mean([abs(x["bias_pp"]) for x in folds])),
      "rarity":rarity,"count_thresholds":thresholds,"folds":folds}

def main(feature_csv,actual_csv,draft_oof_csv,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_csv);a=pd.read_csv(actual_csv);dr=pd.read_csv(draft_oof_csv)
    if any("FIN" in set(x.set.astype(str).str.upper()) for x in [f,a,dr]):raise SystemExit("FIN guard")
    d=f[f.set.isin(SETS)].merge(a,on=["set","name"],how="inner").merge(dr[["set","name","pred_gih_oof"]],on=["set","name"],how="left")
    if d.pred_gih_oof.isna().any():raise SystemExit("draft OOF missing")
    if set(d.set)!=set(SETS):raise SystemExit("set guard")
    kinds=["BASE","WEIGHT_SQRT","WEIGHT_LOG","CENTERED","CENTERED_WEIGHT","DRAFT_AUX","DRAFT_AUX_WEIGHT"]
    results={};preds={}
    for k in kinds:
        p=oof(d,k);preds[k]=p;results[k]=metrics(d,p)
        print("DONE",k,json.dumps({x:results[k][x] for x in ["mae_pp","sqrt_count_weighted_mae_pp","spearman","macro_set_mae_pp","macro_set_spearman","mean_abs_set_bias_pp"]}))
    # Cheap fixed blends are diagnostic only. Both components are set-OOF, but train-fold draft features are not outer-nested.
    for w in [0.25,0.5,0.75]:
        k=f"BLEND_BASE_DRAFT_{w}"
        p=(1-w)*preds["BASE"]+w*d.pred_gih_oof.to_numpy(float)
        results[k]=metrics(d,p);preds[k]=p
    best=min(kinds,key=lambda k:results[k]["mae_pp"])
    save=d[["set","name","rarity_ord","sealed_gih","sealed_gih_count","pred_gih_oof"]].copy()
    for k,p in preds.items():save[k]=p
    save.to_csv(out/"sealed_gih_improvement_oof.csv",index=False)
    rep={"fin_used":False,"mh3_used":False,"sets":SETS,
      "note":"DRAFT_AUX is exploratory: held set draft feature is OOF, but training-row draft OOF predictions may have used the outer held set in their draft-model training. If material improvement appears, rebuild with fully nested cross-fitting before adoption.",
      "results":results,"best_primary":best}
    (out/"sealed_gih_improvement_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"best_primary":best,
      "primary":{k:{x:results[k][x] for x in ["mae_pp","sqrt_count_weighted_mae_pp","spearman","macro_set_mae_pp","macro_set_spearman","mean_abs_set_bias_pp"]} for k in kinds},
      "blend":{k:{x:results[k][x] for x in ["mae_pp","spearman"]} for k in results if k.startswith("BLEND")},
      "base_rarity":results["BASE"]["rarity"],"best_rarity":results[best]["rarity"],
      "base_thresholds":results["BASE"]["count_thresholds"],"best_thresholds":results[best]["count_thresholds"]}))
if __name__=="__main__":main(*sys.argv[1:5])
