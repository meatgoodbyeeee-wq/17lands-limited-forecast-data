#!/usr/bin/env python3
import json, gzip, re, sys, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge, HuberRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEV={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
FEATURES=["mean_mv","cheap_creature_share","cheap_interaction_share","card_advantage_share","evasion_share"]

def fetch_targets():
    with urllib.request.urlopen("https://www.17lands.com/data/play_draw", timeout=30) as r:
        obj=json.load(r)
    rows=obj["data"] if isinstance(obj,dict) else obj
    out={}
    for x in rows:
        s=str(x.get("expansion","")).upper()
        if s in DEV and x.get("event_type")=="PremierDraft":
            out[s]=float(x["average_game_length"])
    if set(out)!=DEV:
        raise SystemExit(f"missing speed targets: {sorted(DEV-set(out))}")
    return out

def aggregate_dev(path):
    d=pd.read_csv(path)
    sets=set(d["set"].astype(str).str.upper())
    if "FIN" in sets or sets!=DEV: raise SystemExit("FIN/set guard failed")
    d=d[(d["rarity_ord"].isin([0,1])) & (d["type_land"]==0)].copy()
    rows=[]
    for s,g in d.groupby("set"):
        creatures=g[g.type_creature==1]
        rows.append({
            "set":s,
            "start_date":pd.to_datetime(g.window_start.iloc[0]),
            "mean_mv":float(g.mv.mean()),
            "cheap_creature_share":float((creatures.mv<=2).mean()) if len(creatures) else 0,
            "cheap_interaction_share":float(g.cheap_interaction.mean()),
            "card_advantage_share":float(g.card_advantage.mean()),
            "evasion_share":float(g.evasion.mean()),
        })
    return pd.DataFrame(rows)

def num(v):
    try:return float(v)
    except:return np.nan

def fra_card_features(c):
    text=(c.get("oracle_text") or "").lower()
    typ=(c.get("type_line") or "").lower()
    mv=num(c.get("cmc",c.get("mv",0)))
    if not np.isfinite(mv): mv=0
    is_creature=int("creature" in typ)
    interaction=int(bool(re.search(r"destroy target|exile target|target creature gets -|deals? [^.]*damage to (any target|target creature|target permanent)|return target .* to (its|their) owner.?s hand",text)))
    cheap_interaction=int(interaction and mv<=3)
    card_advantage=int(bool(re.search(r"draw (two|three|x|that many) cards",text)) or ("create" in text and "token" in text and ("enters" in text or "enter the battlefield" in text)))
    evasion=int(any(k in text for k in ["flying","menace","can't be blocked","cannot be blocked"]))
    return mv,is_creature,cheap_interaction,card_advantage,evasion

def aggregate_fra(path):
    with gzip.open(path,"rt",encoding="utf-8") as f: root=json.load(f)
    cards=root.get("cards") or root.get("forecast",{}).get("cards") or root.get("target",{}).get("cards")
    if not cards: raise SystemExit("FRA cards not found")
    vals=[]
    for c in cards:
        if c.get("rarity") not in {"common","uncommon"}: continue
        if "land" in (c.get("type_line") or "").lower(): continue
        vals.append(fra_card_features(c))
    a=np.array(vals,float)
    creatures=a[a[:,1]==1]
    return {
      "mean_mv":float(a[:,0].mean()),
      "cheap_creature_share":float((creatures[:,0]<=2).mean()) if len(creatures) else 0,
      "cheap_interaction_share":float(a[:,2].mean()),
      "card_advantage_share":float(a[:,3].mean()),
      "evasion_share":float(a[:,4].mean()),
      "n_cu_nonland":int(len(a)),
    }

def make_model(kind):
    if kind=="RIDGE":
        return make_pipeline(StandardScaler(),Ridge(alpha=10.0))
    if kind=="HUBER":
        return make_pipeline(StandardScaler(),HuberRegressor(epsilon=1.35,alpha=0.01,max_iter=2000))
    raise ValueError(kind)

def loso(df,kind):
    pred=[]; truth=[]; fold=[]
    for s in df.set:
        tr=df.set.ne(s); te=~tr
        m=make_model(kind);m.fit(df.loc[tr,FEATURES],df.loc[tr,"turns"])
        p=float(m.predict(df.loc[te,FEATURES])[0]); y=float(df.loc[te,"turns"].iloc[0])
        pred.append(p);truth.append(y);fold.append({"set":s,"actual":y,"pred":p,"abs_err":abs(y-p)})
    return {"mae":float(np.mean(np.abs(np.array(truth)-np.array(pred)))),
            "rmse":float(np.sqrt(np.mean((np.array(truth)-np.array(pred))**2))),
            "folds":fold, "errors":np.array(truth)-np.array(pred)}

def baseline_loso(df):
    folds=[]
    for s in df.set:
        y=float(df.loc[df.set.eq(s),"turns"].iloc[0])
        p=float(df.loc[df.set.ne(s),"turns"].mean())
        folds.append({"set":s,"actual":y,"pred":p,"abs_err":abs(y-p)})
    e=np.array([x["actual"]-x["pred"] for x in folds])
    return {"mae":float(np.mean(np.abs(e))),"rmse":float(np.sqrt(np.mean(e**2))),"folds":folds,"errors":e}

def forward(df,kind,min_train=8):
    d=df.sort_values("start_date").reset_index(drop=True)
    folds=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i]; te=d.iloc[[i]]
        if kind=="MEAN": p=float(tr.turns.mean())
        else:
            m=make_model(kind);m.fit(tr[FEATURES],tr.turns);p=float(m.predict(te[FEATURES])[0])
        y=float(te.turns.iloc[0])
        folds.append({"set":te.set.iloc[0],"n_train":i,"actual":y,"pred":p,"abs_err":abs(y-p)})
    return {"mae":float(np.mean([x["abs_err"] for x in folds])),"folds":folds}

def main(dev_csv,fra_gz,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    targets=fetch_targets()
    df=aggregate_dev(dev_csv)
    df["turns"]=df.set.map(targets)
    fra=aggregate_fra(fra_gz)

    res={"MEAN":baseline_loso(df)}
    for k in ["RIDGE","HUBER"]:res[k]=loso(df,k)
    fw={k:forward(df,k) for k in ["MEAN","RIDGE","HUBER"]}

    # Nested inner-LOSO selection among fixed candidates for each outer fold.
    selected=[]; outer_preds=[]
    for hold in df.set:
        tr=df[df.set.ne(hold)].copy(); te=df[df.set.eq(hold)]
        inner_scores={}
        # mean
        es=[]
        for inn in tr.set:
            y=float(tr.loc[tr.set.eq(inn),"turns"].iloc[0]);p=float(tr.loc[tr.set.ne(inn),"turns"].mean());es.append(abs(y-p))
        inner_scores["MEAN"]=float(np.mean(es))
        for kind in ["RIDGE","HUBER"]:
            inner_scores[kind]=loso(tr,kind)["mae"]
        choice=min(inner_scores,key=inner_scores.get)
        if choice=="MEAN":p=float(tr.turns.mean())
        else:
            m=make_model(choice);m.fit(tr[FEATURES],tr.turns);p=float(m.predict(te[FEATURES])[0])
        y=float(te.turns.iloc[0])
        selected.append({"outer":hold,"selected":choice,"inner_mae":inner_scores})
        outer_preds.append({"set":hold,"actual":y,"pred":p,"abs_err":abs(y-p),"selected":choice})
    nested_mae=float(np.mean([x["abs_err"] for x in outer_preds]))

    # Production: choose model by lowest nested-independent global LOSO only if clearly beats mean.
    best=min(["RIDGE","HUBER"], key=lambda k:res[k]["mae"])
    chosen=best if res[best]["mae"] < res["MEAN"]["mae"] else "MEAN"
    if chosen=="MEAN":
        fra_pred=float(df.turns.mean())
    else:
        m=make_model(chosen);m.fit(df[FEATURES],df.turns)
        fra_pred=float(m.predict(pd.DataFrame([fra])[FEATURES])[0])
    err=np.abs(res[chosen]["errors"])
    interval80=float(np.quantile(err,.8,method="higher"))
    interval90=float(np.quantile(err,.9,method="higher"))

    report={
      "fin_used":False,
      "target":"17Lands Format Speed PremierDraft average_game_length (current all-time value)",
      "n_sets":len(df),
      "features":FEATURES,
      "feature_table":df.to_dict("records"),
      "fra_features":fra,
      "LOSO":{k:{"mae":res[k]["mae"],"rmse":res[k]["rmse"],"folds":res[k]["folds"]} for k in res},
      "forward":fw,
      "nested":{"mae":nested_mae,"selection":selected,"outer":outer_preds},
      "production":{"chosen":chosen,"fra_pred_turns":fra_pred,"interval80_halfwidth":interval80,"interval90_halfwidth":interval90}
    }
    (out/"format_speed_validation.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    df.to_csv(out/"format_speed_features_targets.csv",index=False)
    print("SUMMARY",json.dumps({
      "targets":targets,
      "loso":{k:{"mae":res[k]["mae"],"rmse":res[k]["rmse"]} for k in res},
      "forward":{k:{"mae":fw[k]["mae"]} for k in fw},
      "nested_mae":nested_mae,
      "nested_selection_counts":{k:sum(x["selected"]==k for x in selected) for k in ["MEAN","RIDGE","HUBER"]},
      "fra_features":fra,
      "production":report["production"]
    }))
if __name__=="__main__":
    main(sys.argv[1],sys.argv[2],sys.argv[3])
