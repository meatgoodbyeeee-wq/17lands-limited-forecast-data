#!/usr/bin/env python3
import sys,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge,LinearRegression,HuberRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SETS=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
PAIRS=["WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"]; ORDER="WUBRG"
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number",
      "sealed_gih","sealed_gih_count","sealed_gih_wins"}

def numcols(d):
    return [c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]

def card_oof_all(f,a):
    train=f[f.set.isin(SETS)].merge(a,on=["set","name"],how="inner")
    allf=f[f.set.isin(SETS)].copy()
    nums=numcols(train)
    out=[]
    for hold in SETS:
        tr=train.set.ne(hold)
        tree=make_pipeline(SimpleImputer(strategy="median"),
            ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
        tree.fit(train.loc[tr,nums],train.loc[tr,"sealed_gih"])
        tx=train.loc[tr,"oracle_text"].fillna("")+" TYPE "+train.loc[tr,"type_line"].fillna("")
        text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
        text.fit(tx,train.loc[tr,"sealed_gih"])
        q=allf[allf.set.eq(hold)].copy()
        raw=.7*tree.predict(q[nums])+.3*text.predict(q.oracle_text.fillna("")+" TYPE "+q.type_line.fillna(""))
        center=float(train.loc[tr,"sealed_gih"].mean())
        q["pred_sealed_gih_oof"]=center+1.25*(raw-center)
        out.append(q)
    return pd.concat(out,ignore_index=True)

def pair_features(cards):
    rows=[]
    for s,g in cards.groupby("set"):
        for p in PAIRS:
            m=(g.n_colors>0)
            for c in ORDER:
                if c not in p:m &= g[f"color_{c}"].eq(0)
            cu=g[m & g.rarity_ord.isin([0,1])]
            rm=g[m & g.rarity_ord.isin([2,3])]
            allr=g[m & g.rarity_ord.isin([0,1,2,3])]
            if cu.empty or rm.empty:raise RuntimeError(f"{s} {p} empty group cu={len(cu)} rm={len(rm)}")
            rows.append({"set":s,"pair":p,"cu_mean":float(cu.pred_sealed_gih_oof.mean()),
              "rm_mean":float(rm.pred_sealed_gih_oof.mean()),"all_mean":float(allr.pred_sealed_gih_oof.mean()),
              "n_cu":len(cu),"n_rm":len(rm)})
    q=pd.DataFrame(rows)
    for c in ["cu_mean","rm_mean","all_mean"]:
        q[c+"_c"]=q[c]-q.groupby("set")[c].transform("mean")
    return q

CANDS={
 "CU_OLS":(["cu_mean_c"],"ols"),
 "CU_HUBER":(["cu_mean_c"],"huber"),
 "CU_RM_RIDGE":(["cu_mean_c","rm_mean_c"],"ridge"),
 "CU_RM_HUBER":(["cu_mean_c","rm_mean_c"],"huber"),
 "ALL_HUBER":(["all_mean_c"],"huber"),
}
def model(kind):
    if kind=="ols":return LinearRegression()
    if kind=="ridge":return make_pipeline(StandardScaler(),Ridge(alpha=10.0))
    return make_pipeline(StandardScaler(),HuberRegressor(epsilon=1.35,alpha=0.0001,max_iter=2000,tol=1e-8))

def predict_delta(tr,te,name):
    feat,kind=CANDS[name];m=model(kind);m.fit(tr[feat],tr.actual_delta)
    return m.predict(te[feat])

def inner_score(train,name):
    maes=[];sps=[]
    for hold in sorted(train.set.unique()):
        tr=train[train.set.ne(hold)];te=train[train.set.eq(hold)]
        p=predict_delta(tr,te,name)
        maes.append(float(np.mean(np.abs(te.actual_delta.to_numpy()-p))))
        sps.append(float(spearmanr(te.actual_delta,p).statistic) if len(te)>=3 else np.nan)
    return float(np.mean(maes)),float(np.nanmean(sps))

def fixed_oof(z,name):
    p=np.zeros(len(z));pdlt=np.zeros(len(z))
    for hold in sorted(z.set.unique()):
        tr=z[z.set.ne(hold)];te=z[z.set.eq(hold)]
        dd=predict_delta(tr,te,name)
        mu=float(tr.groupby("set").env_wr.first().mean())
        idx=z.set.eq(hold);pdlt[idx]=dd;p[idx]=mu+dd
    return p,pdlt

def nested_oof(z):
    p=np.zeros(len(z));pdlt=np.zeros(len(z));sel={}
    for hold in sorted(z.set.unique()):
        tr=z[z.set.ne(hold)];te=z[z.set.eq(hold)]
        scores={}
        for name in CANDS:
            ma,sp=inner_score(tr,name);scores[name]={"delta_mae":ma,"spearman":sp}
        choice=min(CANDS,key=lambda n:(scores[n]["delta_mae"],-scores[n]["spearman"]))
        dd=predict_delta(tr,te,choice);mu=float(tr.groupby("set").env_wr.first().mean())
        idx=z.set.eq(hold);pdlt[idx]=dd;p[idx]=mu+dd
        sel[hold]={"selected":choice,"scores":scores}
    return p,pdlt,sel

def metrics(z,p,d):
    folds=[]
    for s,g in z.assign(pred=p,pdelta=d).groupby("set"):
        sp=float(spearmanr(g.actual_wr,g.pred).statistic) if len(g)>=3 else np.nan
        folds.append({"set":s,"n_pairs":len(g),"mae_pp":float(np.mean(np.abs(g.actual_wr-g.pred))*100),
          "delta_mae_pp":float(np.mean(np.abs(g.actual_delta-g.pdelta))*100),"spearman":sp})
    err=np.abs(z.actual_wr.to_numpy()-p)
    return {"mae_pp":float(err.mean()*100),"delta_mae_pp":float(np.mean(np.abs(z.actual_delta.to_numpy()-d))*100),
      "game_weighted_mae_pp":float(np.average(err,weights=z.games)*100),
      "macro_set_mae_pp":float(np.mean([x["mae_pp"] for x in folds])),
      "macro_spearman":float(np.nanmean([x["spearman"] for x in folds])),"folds":folds}

def main(feature_csv,card_actual_csv,color_actual_csv,fra_gih_csv,target_json,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_csv);a=pd.read_csv(card_actual_csv);actual=pd.read_csv(color_actual_csv)
    if any("FIN" in set(x.set.astype(str).str.upper()) for x in [f,a,actual]):raise SystemExit("FIN guard")
    cards=card_oof_all(f,a)
    pf=pair_features(cards)
    env=actual.groupby("set").apply(lambda g:pd.Series({"env_wr":g.wins.sum()/g.games.sum()}),include_groups=False).reset_index()
    z=actual.merge(env,on="set").merge(pf,on=["set","pair"],how="inner")
    z["actual_delta"]=z.actual_wr-z.env_wr
    fixed={}
    fixed_preds={}
    for name in CANDS:
        p,d=fixed_oof(z,name);fixed[name]=metrics(z,p,d);fixed_preds[name]=(p,d)
    npred,ndelta,sel=nested_oof(z); nested=metrics(z,npred,ndelta)

    # Choose fixed model by delta MAE, requiring at least no worse macro spearman than CU_HUBER - .03.
    base_sp=fixed["CU_HUBER"]["macro_spearman"]
    eligible=[n for n in CANDS if fixed[n]["macro_spearman"]>=base_sp-0.03]
    chosen=min(eligible,key=lambda n:fixed[n]["delta_mae_pp"])

    # Final FRA pair features from sealed GIH predictions.
    fg=pd.read_csv(fra_gih_csv)
    target=json.loads(Path(target_json).read_text(encoding="utf-8"))
    tc=target.get("cards") or target.get("forecast",{}).get("cards") or target.get("target",{}).get("cards")
    meta=[]
    for c in tc:
        rar={"common":0,"uncommon":1,"rare":2,"mythic":3}.get(c.get("rarity"),-1)
        colors=set(c.get("colors") or [])
        row={"name":c["name"],"rarity_ord":rar,"n_colors":len(colors)}
        for col in ORDER:row["color_"+col]=int(col in colors)
        meta.append(row)
    fm=pd.DataFrame(meta).merge(fg[["name","sealed_gih_pred"]],on="name",how="inner").rename(columns={"sealed_gih_pred":"pred_sealed_gih_oof"})
    fm["set"]="FRA"
    fra_pf=pair_features(fm)
    feat,kind=CANDS[chosen];m=model(kind);m.fit(z[feat],z.actual_delta)
    hist_env=float(env.env_wr.mean())
    fra_pf["pred_delta"]=m.predict(fra_pf[feat]);fra_pf["pred_wr"]=hist_env+fra_pf.pred_delta
    fra_pf["two_color_mean"]=fra_pf.pred_wr.mean();fra_pf["diff_vs_two_color_mean"]=fra_pf.pred_wr-fra_pf.two_color_mean
    fra_pf.sort_values("pred_wr",ascending=False).to_csv(out/"sealed_fra_two_color_predictions.csv",index=False)

    cards[["set","name","rarity_ord","pred_sealed_gih_oof"]].to_csv(out/"sealed_gih_oof_allcards.csv",index=False)
    z.to_csv(out/"sealed_two_color_training.csv",index=False)
    rep={"fin_used":False,"mh3_used":False,"sets":SETS,"n_actual_rows":len(z),"environment_baselines":env.to_dict("records"),
      "candidate_models":CANDS,"fixed":fixed,"nested":{"metrics":nested,"selection":sel},"chosen":chosen,
      "historical_env_baseline":hist_env,
      "fra":fra_pf[["pair","cu_mean","rm_mean","pred_delta","pred_wr","diff_vs_two_color_mean"]].to_dict("records")}
    (out/"sealed_two_color_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"fixed":{n:{k:fixed[n][k] for k in ["mae_pp","delta_mae_pp","game_weighted_mae_pp","macro_spearman"]} for n in CANDS},
      "nested":{k:nested[k] for k in ["mae_pp","delta_mae_pp","game_weighted_mae_pp","macro_spearman"]},
      "selection_counts":{n:sum(v["selected"]==n for v in sel.values()) for n in CANDS},
      "chosen":chosen,"hist_env":hist_env,
      "fra":[{"pair":r["pair"],"wr":r["pred_wr"],"delta_mean":r["diff_vs_two_color_mean"]} for r in rep["fra"]]}))
if __name__=="__main__":main(*sys.argv[1:7])
