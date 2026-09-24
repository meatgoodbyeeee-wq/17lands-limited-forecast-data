#!/usr/bin/env python3
import json,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import HuberRegressor,LinearRegression

DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}

def prep(path):
    z=pd.read_csv(path)
    sets=set(z["set"].astype(str).str.upper())
    if "FIN" in sets or sets!=DEV: raise SystemExit(f"FIN contamination/set mismatch: {sorted(sets)}")
    if len(z)!=220: raise SystemExit(f"expected 220 rows, got {len(z)}")
    z["env_wr_weighted"]=z.groupby("set",group_keys=False).apply(
        lambda g: pd.Series(np.repeat(g["wins"].sum()/g["games"].sum(),len(g)),index=g.index),
        include_groups=False
    ).sort_index()
    z["delta_weighted"]=z["actual_wr"]-z["env_wr_weighted"]
    z["gih_centered"]=z["gih_simple_mean"]-z.groupby("set")["gih_simple_mean"].transform("mean")
    return z

def model(kind):
    if kind=="OLS": return LinearRegression()
    return HuberRegressor(epsilon=1.35,alpha=0.0001,max_iter=2000,tol=1e-8)

def eval_rows(z,pred,delta):
    folds=[]
    for s,g in z.assign(pred=pred,pdelta=delta).groupby("set"):
        folds.append({
            "set":s,
            "mae_pp":float(np.mean(np.abs(g.actual_wr-g.pred))*100),
            "delta_mae_pp":float(np.mean(np.abs(g.delta_weighted-g.pdelta))*100),
            "spearman":float(spearmanr(g.actual_wr,g.pred).statistic),
            "top2_recall":float(len(set(np.argsort(g.actual_wr.to_numpy())[-2:])&set(np.argsort(g.pred.to_numpy())[-2:]))/2),
            "bottom2_recall":float(len(set(np.argsort(g.actual_wr.to_numpy())[:2])&set(np.argsort(g.pred.to_numpy())[:2]))/2),
        })
    e=np.abs(z.actual_wr.to_numpy()-pred)
    de=np.abs(z.delta_weighted.to_numpy()-delta)
    return {
        "mae_pp":float(e.mean()*100),
        "delta_mae_pp":float(de.mean()*100),
        "mean_set_spearman":float(np.nanmean([x["spearman"] for x in folds])),
        "mean_top2_recall":float(np.mean([x["top2_recall"] for x in folds])),
        "mean_bottom2_recall":float(np.mean([x["bottom2_recall"] for x in folds])),
        "game_weighted_mae_pp":float(np.average(e,weights=z.games)*100),
        "folds":folds,
    }

def loso(z,kind):
    pred=np.zeros(len(z)); delta=np.zeros(len(z)); coef={}
    for hold in sorted(DEV):
        tr=z.set.ne(hold); te=~tr
        mu=float(z.loc[tr].groupby("set")["env_wr_weighted"].first().mean())
        m=model(kind); m.fit(z.loc[tr,["gih_centered"]],z.loc[tr,"delta_weighted"])
        dd=m.predict(z.loc[te,["gih_centered"]])
        delta[te]=dd; pred[te]=mu+dd
        coef[hold]={"mu":mu,"coef":float(m.coef_[0]),"intercept":float(m.intercept_)}
    return pred,delta,coef

def nested_choice(z):
    out={}
    for outer in sorted(DEV):
        train=z[z.set.ne(outer)].copy()
        score={}
        for kind in ["OLS","HUBER"]:
            errs=[]
            for inner in sorted(train.set.unique()):
                tr=train.set.ne(inner); te=~tr
                m=model(kind); m.fit(train.loc[tr,["gih_centered"]],train.loc[tr,"delta_weighted"])
                dd=m.predict(train.loc[te,["gih_centered"]])
                errs.extend(np.abs(train.loc[te,"delta_weighted"].to_numpy()-dd))
            score[kind]=float(np.mean(errs)*100)
        out[outer]={"selected":min(score,key=score.get),"inner_delta_mae_pp":score}
    return out

def forward(z,kind,min_train=8):
    meta=z.groupby("set")[["start_date"]].first().reset_index()
    meta["start_date"]=pd.to_datetime(meta.start_date)
    order=meta.sort_values("start_date").set.tolist()
    rows=[]
    for i in range(min_train,len(order)):
        hold=order[i]; past=set(order[:i])
        tr=z.set.isin(past); te=z.set.eq(hold)
        mu=float(z.loc[tr].groupby("set")["env_wr_weighted"].first().mean())
        m=model(kind); m.fit(z.loc[tr,["gih_centered"]],z.loc[tr,"delta_weighted"])
        dd=m.predict(z.loc[te,["gih_centered"]]); pp=mu+dd
        g=z.loc[te]
        rows.append({"set":hold,"n_train_sets":i,
          "mae_pp":float(np.mean(np.abs(g.actual_wr.to_numpy()-pp))*100),
          "delta_mae_pp":float(np.mean(np.abs(g.delta_weighted.to_numpy()-dd))*100),
          "spearman":float(spearmanr(g.actual_wr,pp).statistic)})
    return {"n_test_sets":len(rows),"mae_pp":float(np.mean([r["mae_pp"] for r in rows])),
            "delta_mae_pp":float(np.mean([r["delta_mae_pp"] for r in rows])),
            "mean_set_spearman":float(np.nanmean([r["spearman"] for r in rows])),"folds":rows}

def intervals(z,pred,delta):
    ae=np.abs(z.actual_wr.to_numpy()-pred)*100
    ade=np.abs(z.delta_weighted.to_numpy()-delta)*100
    qs=[0.5,0.68,0.8,0.9,0.95]
    return {"absolute_wr_abs_error_pp":{str(q):float(np.quantile(ae,q,method="higher")) for q in qs},
            "relative_delta_abs_error_pp":{str(q):float(np.quantile(ade,q,method="higher")) for q in qs}}

def main():
    inp=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
    z=prep(inp)
    results={}
    preds={}
    for kind in ["OLS","HUBER"]:
        p,d,c=loso(z,kind); results[kind]=eval_rows(z,p,d); results[kind]["coefficients"]=c; preds[kind]=(p,d)
    nested=nested_choice(z)
    forward_res={k:forward(z,k) for k in ["OLS","HUBER"]}
    p,d=preds["HUBER"]
    iv=intervals(z,p,d)
    full=model("HUBER"); full.fit(z[["gih_centered"]],z["delta_weighted"])
    env_by_set=z.groupby("set")["env_wr_weighted"].first()
    production={"model":"HuberRegressor","epsilon":1.35,"alpha":0.0001,"max_iter":2000,
      "coef":float(full.coef_[0]),"intercept":float(full.intercept_),
      "environment_baseline":float(env_by_set.mean()),
      "environment_baseline_definition":"equal-weight mean across historical set-level pure-two-color game-weighted win rates",
      "pair_feature":"C/U eligible pair predicted GIH mean minus equal mean of the 10 pair GIH means",
      "target_delta":"pair win rate minus that set's game-weighted pure-two-color win rate"}
    z["huber_pred_wr"]=p; z["huber_pred_delta"]=d; z["env_wr_weighted"]=z["env_wr_weighted"]
    z.to_csv(out/"deck_color_final_oof.csv",index=False)
    report={"fin_used":False,"n_sets":22,"n_rows":220,"target_environment":"game-weighted pure-two-color win rate",
      "LOSO":{"OLS":results["OLS"],"HUBER":results["HUBER"]},
      "nested_choice":nested,"forward_backtest":forward_res,
      "uncertainty":iv,"production_fit":production}
    (out/"deck_color_final_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("FINAL_SUMMARY",json.dumps({
      "OLS":{k:results["OLS"][k] for k in ["mae_pp","delta_mae_pp","mean_set_spearman","game_weighted_mae_pp"]},
      "HUBER":{k:results["HUBER"][k] for k in ["mae_pp","delta_mae_pp","mean_set_spearman","game_weighted_mae_pp"]},
      "nested_huber_selected":sum(v["selected"]=="HUBER" for v in nested.values()),
      "forward":forward_res,"uncertainty":iv,"production":production}))
if __name__=="__main__": main()
