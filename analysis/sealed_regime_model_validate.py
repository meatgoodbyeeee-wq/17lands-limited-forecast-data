#!/usr/bin/env python3
import sys,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr

SETS=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
REGIMES=["PURE2","PAIR_SPLASH","MAIN3PLUS"]
ORDER="WUBRG"

def card_quality(feature_csv,gih_csv):
    f=pd.read_csv(feature_csv)
    p=pd.read_csv(gih_csv)
    d=f[f.set.isin(SETS)].merge(p[["set","name","pred_sealed_gih_oof"]],on=["set","name"],how="inner")
    if "FIN" in set(d.set.astype(str).str.upper()): raise SystemExit("FIN guard")
    return d

def add_quality(actual,cards):
    rows=[]
    for _,r in actual.iterrows():
        if r.regime not in REGIMES: continue
        key=str(r.color_key)
        cs=set(key)
        g=cards[cards.set.eq(r.set)]
        m=g.rarity_ord.isin([0,1,2,3]) & g.n_colors.gt(0)
        for c in ORDER:
            if c not in cs: m &= g[f"color_{c}"].eq(0)
        h=g[m]
        if h.empty: continue
        vals=h.pred_sealed_gih_oof.astype(float)
        rows.append({**r.to_dict(),
            "quality_mean":float(vals.mean()),
            "quality_top25":float(vals.nlargest(max(1,int(np.ceil(len(vals)*.25)))).mean()),
            "quality_p75":float(vals.quantile(.75)),
            "n_eligible":len(vals)})
    z=pd.DataFrame(rows)
    # Target is relative strength within each set/regime, so environment-level differences do not leak into slope.
    env=z.groupby(["set","regime"]).apply(
        lambda g: pd.Series({"env_wr":float(np.average(g.actual_wr,weights=g.games))}),include_groups=False
    ).reset_index()
    z=z.merge(env,on=["set","regime"])
    z["actual_delta"]=z.actual_wr-z.env_wr
    for c in ["quality_mean","quality_top25","quality_p75"]:
        z[c+"_c"]=z[c]-z.groupby(["set","regime"])[c].transform("mean")
    return z

def fit_huber(tr,features):
    sc=StandardScaler()
    X=sc.fit_transform(tr[features])
    m=HuberRegressor(epsilon=1.35,alpha=0.0001,max_iter=2000,tol=1e-8)
    m.fit(X,tr.actual_delta,sample_weight=np.sqrt(tr.games.to_numpy(float)))
    return sc,m

def pred_huber(tr,te,features):
    sc,m=fit_huber(tr,features)
    return m.predict(sc.transform(te[features]))

FEATURES=["quality_mean_c"]

def group_for(strategy,regime):
    if strategy=="POOLED": return "ALL"
    if strategy=="SPLIT2": return "PURE2" if regime=="PURE2" else "NONPURE"
    if strategy=="SPLIT3": return regime
    raise ValueError(strategy)

def oof(z,strategy):
    pred=np.full(len(z),np.nan); pdelta=np.full(len(z),np.nan)
    for hold in SETS:
        train=z[z.set.ne(hold)]
        test=z[z.set.eq(hold)]
        for regime in REGIMES:
            te=test[test.regime.eq(regime)]
            if te.empty: continue
            grp=group_for(strategy,regime)
            if strategy=="POOLED":
                tr=train
            elif strategy=="SPLIT2":
                tr=train[train.regime.eq("PURE2")] if grp=="PURE2" else train[train.regime.isin(["PAIR_SPLASH","MAIN3PLUS"])]
            else:
                tr=train[train.regime.eq(regime)]
            dd=pred_huber(tr,te,FEATURES)
            # Absolute baseline stays regime-specific; comparison tests the slope/model split, not baseline definitions.
            env_train=train[train.regime.eq(regime)].groupby("set").env_wr.first()
            mu=float(env_train.mean()) if len(env_train) else float(train.groupby("set").env_wr.first().mean())
            idx=te.index.to_numpy()
            pdelta[idx]=dd; pred[idx]=mu+dd
    return pred,pdelta

def metrics(z,p,d):
    ok=np.isfinite(p)
    q=z[ok].copy(); pp=p[ok]; dd=d[ok]
    err=np.abs(q.actual_wr.to_numpy()-pp)
    de=np.abs(q.actual_delta.to_numpy()-dd)
    per={}
    for reg in REGIMES:
        m=q.regime.eq(reg).to_numpy()
        if not m.any(): continue
        sp=float(spearmanr(q.actual_wr.to_numpy()[m],pp[m]).statistic)
        per[reg]={"n":int(m.sum()),"games":int(q.games.to_numpy()[m].sum()),
          "mae_pp":float(err[m].mean()*100),"delta_mae_pp":float(de[m].mean()*100),
          "game_weighted_mae_pp":float(np.average(err[m],weights=q.games.to_numpy(float)[m])*100),
          "spearman":sp}
    return {"n":len(q),"mae_pp":float(err.mean()*100),"delta_mae_pp":float(de.mean()*100),
      "game_weighted_mae_pp":float(np.average(err,weights=q.games)*100),
      "spearman":float(spearmanr(q.actual_wr,pp).statistic),"per_regime":per}

def set_regime_summary(z):
    e=z.groupby(["set","regime"]).agg(games=("games","sum"),wins=("wins","sum")).reset_index()
    e["wr"]=e.wins/e.games
    wide=e.pivot(index="set",columns="regime",values=["games","wr"])
    return e.to_dict("records")

def main(feature_csv,gih_csv,actual_csv,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    actual=pd.read_csv(actual_csv)
    if "FIN" in set(actual.set.astype(str).str.upper()):raise SystemExit("FIN guard")
    cards=card_quality(feature_csv,gih_csv)
    z=add_quality(actual,cards)
    # Reliability floor established before this model comparison.
    z=z[z.games>=100].copy().reset_index(drop=True)
    if set(z.regime)!=set(REGIMES):raise SystemExit(f"missing regime {set(z.regime)}")
    results={}
    preds={}
    for strategy in ["POOLED","SPLIT2","SPLIT3"]:
        p,d=oof(z,strategy)
        results[strategy]=metrics(z,p,d)
        preds[strategy]=(p,d)
    # Also show slope behavior on full data for interpretation only.
    slopes={}
    for strategy in ["POOLED","SPLIT2","SPLIT3"]:
        groups={}
        labels=["ALL"] if strategy=="POOLED" else (["PURE2","NONPURE"] if strategy=="SPLIT2" else REGIMES)
        for lab in labels:
            if lab=="ALL":tr=z
            elif lab=="NONPURE":tr=z[z.regime.isin(["PAIR_SPLASH","MAIN3PLUS"])]
            else:tr=z[z.regime.eq(lab)]
            sc,m=fit_huber(tr,FEATURES)
            # Convert standardized coef to raw delta per 1.0 GIH-WR unit.
            raw=float(m.coef_[0]/sc.scale_[0])
            groups[lab]={"raw_quality_slope":raw,"n":len(tr),"games":int(tr.games.sum())}
        slopes[strategy]=groups
    save=z.copy()
    for strategy,(p,d) in preds.items():
        save[strategy.lower()+"_pred_wr"]=p
        save[strategy.lower()+"_pred_delta"]=d
    save.to_csv(out/"sealed_regime_model_predictions.csv",index=False)
    rep={"fin_used":False,"mh3_used":False,"sets":SETS,"min_games_per_group":100,
      "feature":"mean OOF-predicted Sealed GIH of cards whose colors are a subset of the deck color key; all rarities",
      "strategies":{"POOLED":"one common slope","SPLIT2":"Pure 2C vs non-Pure","SPLIT3":"Pure 2C vs 2C+Splash vs 3C+"},
      "results":results,"slopes":slopes,"set_regime_summary":set_regime_summary(z)}
    (out/"sealed_regime_model_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"rows":len(z),"counts":z.groupby("regime").size().to_dict(),
      "results":{k:{m:v[m] for m in ["mae_pp","delta_mae_pp","game_weighted_mae_pp","spearman"]} for k,v in results.items()},
      "per_regime":{k:v["per_regime"] for k,v in results.items()},"slopes":slopes}))
if __name__=="__main__":main(*sys.argv[1:5])
