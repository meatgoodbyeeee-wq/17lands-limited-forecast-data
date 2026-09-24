#!/usr/bin/env python3
import json, gzip, re, sys, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ALL22={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
DEV=ALL22-{"MH3"}
FEATURES=["mean_mv","cheap_creature_share","cheap_interaction_share","card_advantage_share","evasion_share"]

def fetch_targets():
    with urllib.request.urlopen("https://www.17lands.com/data/play_draw",timeout=30) as r:
        rows=json.load(r)["data"]
    out={str(x["expansion"]).upper():float(x["average_game_length"]) for x in rows
         if str(x.get("expansion","")).upper() in DEV and x.get("event_type")=="PremierDraft"}
    if set(out)!=DEV: raise SystemExit(f"missing targets {sorted(DEV-set(out))}")
    return out

def aggregate_dev(path):
    d=pd.read_csv(path)
    sets=set(d["set"].astype(str).str.upper())
    if "FIN" in sets or sets!=ALL22: raise SystemExit("FIN/set guard failed")
    d=d[d["set"].ne("MH3") & d["rarity_ord"].isin([0,1]) & d["type_land"].eq(0)].copy()
    rows=[]
    for s,g in d.groupby("set"):
        cr=g[g.type_creature.eq(1)]
        rows.append({"set":s,"start_date":pd.to_datetime(g.window_start.iloc[0]),
          "mean_mv":float(g.mv.mean()),
          "cheap_creature_share":float((cr.mv<=2).mean()),
          "cheap_interaction_share":float(g.cheap_interaction.mean()),
          "card_advantage_share":float(g.card_advantage.mean()),
          "evasion_share":float(g.evasion.mean())})
    return pd.DataFrame(rows)

def fra_features(path):
    with gzip.open(path,"rt",encoding="utf-8") as f: root=json.load(f)
    cards=root.get("cards") or root.get("forecast",{}).get("cards") or root.get("target",{}).get("cards")
    vals=[]
    for c in cards:
        if c.get("rarity") not in {"common","uncommon"}: continue
        typ=(c.get("type_line") or "").lower()
        if "land" in typ: continue
        text=(c.get("oracle_text") or "").lower()
        mv=float(c.get("cmc",c.get("mv",0)) or 0)
        creature=int("creature" in typ)
        interaction=int(bool(re.search(r"destroy target|exile target|target creature gets -|deals? [^.]*damage to (any target|target creature|target permanent)|return target .* to (its|their) owner.?s hand",text)))
        vals.append((mv,creature,int(interaction and mv<=3),
          int(bool(re.search(r"draw (two|three|x|that many) cards",text)) or ("create" in text and "token" in text and ("enters" in text or "enter the battlefield" in text))),
          int(any(k in text for k in ["flying","menace","can't be blocked","cannot be blocked"]))))
    a=np.array(vals,float); cr=a[a[:,1]==1]
    return {"mean_mv":float(a[:,0].mean()),"cheap_creature_share":float((cr[:,0]<=2).mean()),
      "cheap_interaction_share":float(a[:,2].mean()),"card_advantage_share":float(a[:,3].mean()),
      "evasion_share":float(a[:,4].mean())}

def model(): return make_pipeline(StandardScaler(),Ridge(alpha=10.0))

def loso(df):
    folds=[]
    for s in df.set:
        tr=df.set.ne(s); te=~tr
        m=model(); m.fit(df.loc[tr,FEATURES],df.loc[tr,"turns"])
        p=float(m.predict(df.loc[te,FEATURES])[0]); y=float(df.loc[te,"turns"].iloc[0])
        folds.append({"set":s,"actual":y,"pred":p,"abs_err":abs(y-p)})
    e=np.array([x["actual"]-x["pred"] for x in folds])
    return {"mae":float(np.mean(np.abs(e))),"rmse":float(np.sqrt(np.mean(e**2))),"folds":folds,"errors":e}

def baseline(df):
    folds=[]
    for s in df.set:
        y=float(df.loc[df.set.eq(s),"turns"].iloc[0]); p=float(df.loc[df.set.ne(s),"turns"].mean())
        folds.append({"set":s,"actual":y,"pred":p,"abs_err":abs(y-p)})
    return {"mae":float(np.mean([x["abs_err"] for x in folds])),"folds":folds}

def forward(df,kind,min_train=8):
    d=df.sort_values("start_date").reset_index(drop=True); folds=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i]; te=d.iloc[[i]]
        if kind=="MEAN": p=float(tr.turns.mean())
        else:
            m=model(); m.fit(tr[FEATURES],tr.turns); p=float(m.predict(te[FEATURES])[0])
        y=float(te.turns.iloc[0]); folds.append({"set":te.set.iloc[0],"actual":y,"pred":p,"abs_err":abs(y-p)})
    return {"mae":float(np.mean([x["abs_err"] for x in folds])),"n_test":len(folds),"folds":folds}

def main(dev_csv,fra_gz,outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
    df=aggregate_dev(dev_csv); targets=fetch_targets(); df["turns"]=df.set.map(targets)
    fra=fra_features(fra_gz)
    b=baseline(df); r=loso(df)
    fw_b=forward(df,"MEAN"); fw_r=forward(df,"RIDGE")
    m=model(); m.fit(df[FEATURES],df.turns); fra_pred=float(m.predict(pd.DataFrame([fra])[FEATURES])[0])
    ae=np.abs(r["errors"])
    report={"fin_used":False,"mh3_used":False,"n_sets":21,"features":FEATURES,
      "loso":{"MEAN":b,"RIDGE":{"mae":r["mae"],"rmse":r["rmse"],"folds":r["folds"]}},
      "forward":{"MEAN":fw_b,"RIDGE":fw_r},
      "production":{"fra_pred_turns":fra_pred,"interval80_halfwidth":float(np.quantile(ae,.8,method="higher")),
                    "interval90_halfwidth":float(np.quantile(ae,.9,method="higher"))}}
    (out/"format_speed_no_mh3.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"loso_mean":b["mae"],"loso_ridge":r["mae"],"loso_rmse":r["rmse"],
      "forward_mean":fw_b["mae"],"forward_ridge":fw_r["mae"],"forward_n":fw_r["n_test"],
      "fra_pred":fra_pred,"interval80":report["production"]["interval80_halfwidth"],
      "interval90":report["production"]["interval90_halfwidth"]}))
if __name__=="__main__": main(sys.argv[1],sys.argv[2],sys.argv[3])
