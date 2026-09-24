#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.pipeline import make_pipeline

DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
PAIRS=["WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"]
ORDER="WUBRG"
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}

def canon(s):
    return "".join(c for c in ORDER if c in set(str(s).upper()))

def fetch_color(set_code, start_date, end_date):
    params={"expansion":set_code,"event_type":"PremierDraft","start_date":start_date,
            "end_date":end_date,"combine_splash":"false"}
    url="https://www.17lands.com/color_ratings/data?"+urlencode(params)
    req=Request(url,headers={"User-Agent":"LimitedForecastResearch/1.0","Accept":"application/json"})
    with urlopen(req,timeout=60) as r:
        raw=json.load(r)
    if isinstance(raw,dict) and "data" in raw: raw=raw["data"]
    out=[]
    for z in raw:
        if z.get("is_summary"): continue
        short=str(z.get("short_name","")).upper().strip()
        if not re.fullmatch(r"[WUBRG]{2}",short): continue
        p=canon(short)
        if p not in PAIRS: continue
        g=int(z.get("games") or 0); w=int(z.get("wins") or 0)
        if g>0: out.append({"set":set_code,"pair":p,"games":g,"wins":w,"actual_wr":w/g})
    q=pd.DataFrame(out).drop_duplicates(["set","pair"])
    missing=sorted(set(PAIRS)-set(q["pair"])) if len(q) else PAIRS
    if missing: raise RuntimeError(f"{set_code}: missing pure two-color rows {missing}; sample keys={list(raw[0]) if raw else []}")
    return q

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

def pair_features(d):
    rows=[]
    for s,g in d.groupby("set"):
        for p in PAIRS:
            mask=(g["rarity_ord"].isin([0,1])) & (g["n_colors"]>0)
            for c in ORDER:
                if c not in p: mask &= (g[f"color_{c}"]==0)
            vals=g.loc[mask,"pred_gih_oof"].astype(float)
            if vals.empty: raise RuntimeError(f"{s} {p}: no eligible C/U cards")
            rows.append({"set":s,"pair":p,"gih_simple_mean":float(vals.mean()),"n_cards":int(len(vals))})
    return pd.DataFrame(rows)

def metrics(y,p,actual_delta,pdelta,sets,games):
    fold=[]
    for s in sorted(set(sets)):
        m=np.array(sets)==s
        yy=np.asarray(y)[m]; pp=np.asarray(p)[m]
        dd=np.asarray(actual_delta)[m]; pdlt=np.asarray(pdelta)[m]
        sp=spearmanr(yy,pp).statistic
        top=len(set(np.argsort(yy)[-2:]) & set(np.argsort(pp)[-2:]))/2
        bot=len(set(np.argsort(yy)[:2]) & set(np.argsort(pp)[:2]))/2
        fold.append({"set":s,"mae_pp":float(np.mean(abs(yy-pp))*100),
                     "delta_mae_pp":float(np.mean(abs(dd-pdlt))*100),
                     "spearman":float(sp),"top2_recall":top,"bottom2_recall":bot})
    w=np.asarray(games,float); err=np.abs(np.asarray(y)-np.asarray(p))
    return {"mae_pp":float(np.mean(err)*100),
            "delta_mae_pp":float(np.mean(np.abs(np.asarray(actual_delta)-np.asarray(pdelta)))*100),
            "mean_set_spearman":float(np.nanmean([x["spearman"] for x in fold])),
            "mean_top2_recall":float(np.mean([x["top2_recall"] for x in fold])),
            "mean_bottom2_recall":float(np.mean([x["bottom2_recall"] for x in fold])),
            "game_weighted_mae_pp":float(np.average(err,weights=w)*100),
            "folds":fold}

def main():
    inp=Path(sys.argv[1] if len(sys.argv)>1 else "model_in/dev_feature_table.csv")
    out=Path(sys.argv[2] if len(sys.argv)>2 else "model_out")
    out.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(inp)
    sets=set(d["set"].str.upper())
    if "FIN" in sets or sets != DEV: raise SystemExit(f"FIN contamination or set mismatch: {sorted(sets)}")
    windows=d.groupby("set")[["window_start","window_end"]].first().reset_index()
    actual=[]
    for _,r in windows.sort_values("set").iterrows():
        s=r["set"]
        st=pd.Timestamp(r["window_start"]).date()
        en=(pd.Timestamp(r["window_end"])-pd.Timedelta(days=1)).date()
        q=fetch_color(s,st.isoformat(),en.isoformat())
        q["start_date"]=st.isoformat(); q["end_date"]=en.isoformat()
        actual.append(q)
        print("COLOR_FETCH",s,len(q),int(q["games"].sum()))
    actual=pd.concat(actual,ignore_index=True)
    actual.to_csv(out/"deck_color_actuals_28cal.csv",index=False)

    d["pred_gih_oof"]=card_oof(d)
    pf=pair_features(d)
    z=actual.merge(pf,on=["set","pair"],how="inner")
    if len(z)!=len(DEV)*10: raise SystemExit(f"expected {len(DEV)*10} rows got {len(z)}")
    z["actual_set_mean"]=z.groupby("set")["actual_wr"].transform("mean")
    z["actual_delta"]=z["actual_wr"]-z["actual_set_mean"]
    z["gih_centered"]=z["gih_simple_mean"]-z.groupby("set")["gih_simple_mean"].transform("mean")

    pred0=np.zeros(len(z)); delta0=np.zeros(len(z))
    pred1=np.zeros(len(z)); delta1=np.zeros(len(z)); coefs={}
    for hold in sorted(DEV):
        tr=z["set"]!=hold; te=~tr
        train_set_means=z.loc[tr].groupby("set")["actual_wr"].mean()
        mu=float(train_set_means.mean())
        pred0[te]=mu
        m=LinearRegression()
        m.fit(z.loc[tr,["gih_centered"]],z.loc[tr,"actual_delta"])
        dd=m.predict(z.loc[te,["gih_centered"]])
        dd=dd-dd.mean()
        delta1[te]=dd; pred1[te]=mu+dd
        coefs[hold]={"environment_mean":mu,"gih_coef":float(m.coef_[0]),"intercept":float(m.intercept_)}

    z["b0_pred_wr"]=pred0; z["b1_pred_wr"]=pred1; z["b1_pred_delta"]=delta1
    z.to_csv(out/"deck_color_baseline_predictions.csv",index=False)
    report={"fin_used":False,"n_sets":len(DEV),"n_rows":len(z),
            "date_note":"28 calendar dates from the date of existing exact-28d window_start through start+27d; timestamp mismatch versus exact GIH window is retained as a limitation.",
            "B0":metrics(z.actual_wr,pred0,z.actual_delta,delta0,z.set,z.games),
            "B1":metrics(z.actual_wr,pred1,z.actual_delta,delta1,z.set,z.games),
            "coefficients":coefs}
    (out/"deck_color_baseline_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("BASELINE_REPORT",json.dumps({k:v for k,v in report.items() if k in ["B0","B1"]},default=float))
if __name__=="__main__": main()
