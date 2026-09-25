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
sys.path.insert(0,"scripts")
from build_dev_features import card_features

SETS=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number",
      "sealed_gih","sealed_gih_count","sealed_gih_wins"}

def numeric_cols(d):
    return [c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]

def oof_predict(d):
    nums=numeric_cols(d); txt=d["oracle_text"].fillna("")+" TYPE "+d["type_line"].fillna("")
    pred=np.full(len(d),np.nan); rawpred=np.full(len(d),np.nan); centers={}
    for hold in SETS:
        tr=d.set.ne(hold);te=~tr
        tree=make_pipeline(SimpleImputer(strategy="median"),
            ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
        tree.fit(d.loc[tr,nums],d.loc[tr,"sealed_gih"])
        pt=tree.predict(d.loc[te,nums])
        text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
        text.fit(txt[tr],d.loc[tr,"sealed_gih"])
        px=text.predict(txt[te])
        raw=.7*pt+.3*px
        center=float(d.loc[tr,"sealed_gih"].mean())
        rawpred[te]=raw
        pred[te]=center+1.25*(raw-center)
        centers[hold]=center
    return pred,rawpred,centers,nums

def summarize(d,pred,label):
    folds=[]
    for s,g in d.assign(pred=pred).groupby("set"):
        y=g.sealed_gih.to_numpy(float);p=g.pred.to_numpy(float)
        sp=float(spearmanr(y,p).statistic)
        k=min(30,len(g)//5 if len(g)//5>0 else 1)
        folds.append({"set":s,"n":len(g),"mae_pp":float(np.mean(np.abs(y-p))*100),"spearman":sp,
          "top_recall":float(len(set(np.argsort(y)[-k:])&set(np.argsort(p)[-k:]))/k),
          "bottom_recall":float(len(set(np.argsort(y)[:k])&set(np.argsort(p)[:k]))/k)})
    err=np.abs(d.sealed_gih.to_numpy(float)-pred)
    return {"label":label,"n":len(d),"mae_pp":float(err.mean()*100),
      "gih_count_weighted_mae_pp":float(np.average(err,weights=np.sqrt(d.sealed_gih_count.to_numpy(float)))*100),
      "spearman":float(spearmanr(d.sealed_gih,pred).statistic),
      "macro_set_mae_pp":float(np.mean([x["mae_pp"] for x in folds])),
      "macro_set_spearman":float(np.mean([x["spearman"] for x in folds])),
      "macro_top_recall":float(np.mean([x["top_recall"] for x in folds])),
      "macro_bottom_recall":float(np.mean([x["bottom_recall"] for x in folds])),
      "folds":folds}

def fit_full_predict(d,target_cards,nums):
    txt=d["oracle_text"].fillna("")+" TYPE "+d["type_line"].fillna("")
    tree=make_pipeline(SimpleImputer(strategy="median"),
        ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
    tree.fit(d[nums],d["sealed_gih"])
    text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
    text.fit(txt,d["sealed_gih"])
    q=pd.DataFrame([card_features(c) for c in target_cards])
    q["is_supplemental_power_set"]=0;q["is_premier_set"]=1
    for col in nums:
        if col not in q:q[col]=np.nan
    qt=q["oracle_text"].fillna("")+" TYPE "+q["type_line"].fillna("")
    raw=.7*tree.predict(q[nums])+.3*text.predict(qt)
    center=float(d["sealed_gih"].mean())
    q["sealed_gih_pred"]=center+1.25*(raw-center)
    return q

def main(feature_csv,actual_csv,target_json,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_csv);a=pd.read_csv(actual_csv)
    if "FIN" in set(f.set.astype(str).str.upper()) or "FIN" in set(a.set.astype(str).str.upper()):raise SystemExit("FIN guard")
    d=f[f.set.isin(SETS)].merge(a,on=["set","name"],how="inner")
    counts=d.groupby("set").size().to_dict()
    if set(counts)!=set(SETS) or min(counts.values())<150:raise SystemExit(f"merge guard {counts}")
    pred,raw,centers,nums=oof_predict(d)

    same=summarize(d,pred,"same_method_1.25")
    rawm=summarize(d,raw,"blend_no_decompression")
    # Naive held-set baseline: training-card global mean.
    base=np.zeros(len(d))
    for s in SETS:
        tr=d.set.ne(s);te=~tr;base[te]=float(d.loc[tr,"sealed_gih"].mean())
    bm=summarize(d,base,"mean_baseline")

    target=json.loads(Path(target_json).read_text(encoding="utf-8"))
    cards=target.get("cards") or target.get("forecast",{}).get("cards") or target.get("target",{}).get("cards")
    q=fit_full_predict(d,cards,nums)
    q[["name","rarity_ord","n_colors","sealed_gih_pred"]].to_csv(out/"sealed_fra_gih_predictions.csv",index=False)
    d.assign(pred_sealed_gih=pred,raw_sealed_gih=raw)[["set","name","rarity_ord","n_colors","sealed_gih","sealed_gih_count","pred_sealed_gih","raw_sealed_gih"]].to_csv(out/"sealed_gih_oof.csv",index=False)
    rep={"fin_used":False,"mh3_used":False,"sets":SETS,"n_cards":len(d),"merge_counts":counts,
      "model":{"structured":"ExtraTrees 600 leaf8 max_features=.6","text":"TFIDF(1,2)+Ridge10","blend":"70:30","decompression":1.25},
      "mean_baseline":bm,"same_method":same,"no_decompression_diagnostic":rawm,
      "fra":{"n_cards":len(q),"mean_pred":float(q.sealed_gih_pred.mean()),"min_pred":float(q.sealed_gih_pred.min()),"max_pred":float(q.sealed_gih_pred.max())}}
    (out/"sealed_gih_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"baseline":{k:bm[k] for k in ["mae_pp","macro_set_mae_pp","macro_set_spearman"]},
      "same":{k:same[k] for k in ["mae_pp","gih_count_weighted_mae_pp","spearman","macro_set_mae_pp","macro_set_spearman","macro_top_recall","macro_bottom_recall"]},
      "raw":{k:rawm[k] for k in ["mae_pp","macro_set_mae_pp","macro_set_spearman"]},
      "fra":rep["fra"],"counts":counts}))
if __name__=="__main__":main(*sys.argv[1:5])
