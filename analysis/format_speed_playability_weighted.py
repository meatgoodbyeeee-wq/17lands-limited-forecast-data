#!/usr/bin/env python3
import sys,json,gzip,re
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.ensemble import ExtraTreesRegressor,HistGradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
sys.path.insert(0,"analysis")
import format_speed_mechanism_effects as fm
import deck_color_alsa as dca

ALL22={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
DEV=ALL22-{"MH3"}
BASE=fm.BASE
ORDER="WUBRG"; PAIRS=fm.PAIRS
GIH_DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}

def read_json_any(path):
    p=Path(path)
    if p.exists():
        if p.suffix==".gz":
            with gzip.open(p,"rt",encoding="utf-8") as f:return json.load(f)
        return json.loads(p.read_text(encoding="utf-8"))
    q=Path(str(p).removesuffix(".gz"))
    if q.exists():return json.loads(q.read_text(encoding="utf-8"))
    gz=Path(str(q)+".gz")
    if gz.exists():
        with gzip.open(gz,"rt",encoding="utf-8") as f:return json.load(f)
    raise FileNotFoundError(path)

def gih_oof_21(d):
    x=d[d["set"].isin(DEV)].copy().reset_index(drop=True)
    nums=[c for c in x.columns if c not in GIH_DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(x[c])]
    txt=x["oracle_text"].fillna("")+" TYPE "+x["type_line"].fillna("")
    pred=np.full(len(x),np.nan)
    for hold in sorted(DEV):
        tr=x["set"].ne(hold);te=~tr
        tree=make_pipeline(SimpleImputer(strategy="median"),
          ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
        tree.fit(x.loc[tr,nums],x.loc[tr,"actual_gih"])
        pt=tree.predict(x.loc[te,nums])
        text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
        text.fit(txt[tr],x.loc[tr,"actual_gih"])
        px=text.predict(txt[te])
        raw=.7*pt+.3*px
        center=float(x.loc[tr,"actual_gih"].mean())
        pred[te]=center+1.25*(raw-center)
    x["pred_gih_oof"]=pred
    return x

def alsa_oof_21(f,y):
    f=f[f["set"].isin(DEV)].copy().reset_index(drop=True)
    y=y[y["set"].isin(DEV)].copy()
    d=f.merge(y,on=["set","name"],how="inner")
    X=dca.adopted_X(d)
    p=np.full(len(d),np.nan)
    kw=dict(loss="squared_error",max_iter=250,learning_rate=.06,l2_regularization=2,random_state=20260923)
    for hold in sorted(DEV):
        tr=d.set.ne(hold).to_numpy();te=~tr
        m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingRegressor(**kw))
        m.fit(X.loc[tr],d.loc[tr,"actual_alsa"])
        floor=float(d.loc[tr,"actual_alsa"].min())+1e-6
        p[te]=np.maximum(m.predict(X.loc[te]),floor)
    return d[["set","name"]].assign(pred_alsa_oof=p)

def rank_weights(g):
    # Within set+rarity to avoid treating commons/uncommons differently merely because rarity shifts scales.
    gih_pct=g.groupby(["set","rarity_ord"])["pred_gih_oof"].rank(pct=True,method="average")
    alsa_pct=g.groupby(["set","rarity_ord"])["pred_alsa_oof"].rank(pct=True,method="average")
    # Floor avoids making weak-but-playable cards disappear entirely.
    wg=.25+1.5*gih_pct
    wa=.25+1.5*(1.0-alsa_pct)
    wc=np.sqrt(wg*wa)
    return {"UNIFORM":np.ones(len(g)),"GIH":wg.to_numpy(float),"ALSA":wa.to_numpy(float),"COMBINED":wc.to_numpy(float)}

def pair_engine_concentration(g,weights):
    flags=np.array([fm.text_flags(str(r.oracle_text or ""),r.power,bool(r.type_planeswalker))["engine"] for _,r in g.iterrows()],float)
    colors=fm.card_colors_from_hist(g)
    w=np.asarray(weights,float)
    global_density=float(np.sum(w*flags)/np.sum(w))
    pv=[]
    for _,cs in PAIRS.items():
        idx=np.array([bool(col) and col.issubset(cs) for col in colors])
        if idx.any():pv.append(float(np.sum(w[idx]*flags[idx])/np.sum(w[idx])))
    return max(pv)-global_density

def hist_speed_table(features,alsa):
    d=gih_oof_21(features)
    ao=alsa_oof_21(features,alsa)
    d=d.merge(ao,on=["set","name"],how="inner")
    d=d[d["rarity_ord"].isin([0,1]) & d["type_land"].eq(0)].copy()
    tar=fm.targets()
    rows=[]
    for s,g in d.groupby("set"):
        cr=g[g.type_creature.eq(1)]
        ws=rank_weights(g)
        row={"set":s,"start_date":pd.to_datetime(g.window_start.iloc[0]),"turns":tar[s],
          "mean_mv":float(g.mv.mean()),"cheap_creature_share":float((cr.mv<=2).mean()) if len(cr) else 0,
          "cheap_interaction_share":float(g.cheap_interaction.mean()),"card_advantage_share":float(g.card_advantage.mean()),
          "evasion_share":float(g.evasion.mean())}
        for name,w in ws.items():row["engine_conc_"+name.lower()]=pair_engine_concentration(g,w)
        rows.append(row)
    return pd.DataFrame(rows),d

def fra_rows(target_path,forecast_path):
    target=read_json_any(target_path)
    forecast=read_json_any(forecast_path)
    tc=target.get("cards") or target.get("forecast",{}).get("cards") or target.get("target",{}).get("cards")
    fc=forecast.get("forecast",{}).get("cards") or forecast.get("cards")
    pred={c["name"]:c for c in fc}
    rows=[]
    for c in tc:
        if c.get("rarity") not in {"common","uncommon"}:continue
        if "land" in (c.get("type_line") or "").lower():continue
        q=pred.get(c["name"])
        if not q:continue
        r=dict(c)
        r["set"]="FRA"
        r["rarity_ord"]={"common":0,"uncommon":1}[c["rarity"]]
        r["pred_gih_oof"]=float(q["gih"])
        r["pred_alsa_oof"]=float(q["alsa"])
        for col in ORDER:r["color_"+col]=int(col in set(c.get("colors") or []))
        r["type_land"]=0
        r["type_planeswalker"]=int("planeswalker" in (c.get("type_line") or "").lower())
        try:r["power"]=float(c.get("power"))
        except:r["power"]=0.0
        rows.append(r)
    g=pd.DataFrame(rows)
    if len(g)<150:raise SystemExit(f"FRA merge too small: {len(g)}")
    ws=rank_weights(g)
    return {name:pair_engine_concentration(g,w) for name,w in ws.items()},len(g)

CAND={"UNIFORM":"engine_conc_uniform","GIH":"engine_conc_gih","ALSA":"engine_conc_alsa","COMBINED":"engine_conc_combined"}

def feats(name):return BASE+[CAND[name]]
def pred(tr,te,name):
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0));m.fit(tr[feats(name)],tr.turns)
    return m.predict(te[feats(name)])
def loo(df,name):
    e=[]
    for s in df.set:
        tr=df[df.set.ne(s)];te=df[df.set.eq(s)]
        e.append(abs(float(te.turns.iloc[0])-float(pred(tr,te,name)[0])))
    return float(np.mean(e))
def forward(df,name,min_train=8):
    d=df.sort_values("start_date").reset_index(drop=True);e=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i];te=d.iloc[[i]]
        e.append(abs(float(te.turns.iloc[0])-float(pred(tr,te,name)[0])))
    return float(np.mean(e))
def nested(df):
    rows=[]
    for hold in df.set:
        tr=df[df.set.ne(hold)];te=df[df.set.eq(hold)]
        sc={n:loo(tr,n) for n in CAND};ch=min(sc,key=sc.get)
        p=float(pred(tr,te,ch)[0]);y=float(te.turns.iloc[0])
        rows.append({"set":hold,"selected":ch,"actual":y,"pred":p,"abs_err":abs(y-p),"inner":sc})
    return rows
def nested_forward(df,min_train=8):
    d=df.sort_values("start_date").reset_index(drop=True);rows=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i];te=d.iloc[[i]]
        sc={n:loo(tr,n) for n in CAND};ch=min(sc,key=sc.get)
        p=float(pred(tr,te,ch)[0]);y=float(te.turns.iloc[0])
        rows.append({"set":te.set.iloc[0],"selected":ch,"actual":y,"pred":p,"abs_err":abs(y-p),"inner":sc})
    return rows

def main(feature_csv,alsa_csv,target_path,forecast_path,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_csv);a=pd.read_csv(alsa_csv)
    sets=set(f["set"].astype(str).str.upper())
    if "FIN" in sets or sets!=ALL22:raise SystemExit("feature guard")
    if "FIN" in set(a["set"].astype(str).str.upper()):raise SystemExit("ALSA FIN guard")
    df,cards=hist_speed_table(f,a)
    fra,nfra=fra_rows(target_path,forecast_path)
    if len(df)!=21 or "MH3" in set(df.set) or "FIN" in set(df.set):raise SystemExit("speed guard")

    cv={n:loo(df,n) for n in CAND}; fw={n:forward(df,n) for n in CAND}
    outer=nested(df); nf=nested_forward(df)
    om=float(np.mean([x["abs_err"] for x in outer])); nm=float(np.mean([x["abs_err"] for x in nf]))
    oc={n:sum(x["selected"]==n for x in outer) for n in CAND}; nc={n:sum(x["selected"]==n for x in nf) for n in CAND}

    eligible=[n for n in CAND if cv[n] <= cv["UNIFORM"] and fw[n] <= fw["UNIFORM"]]
    chosen=min(eligible,key=lambda n:cv[n]+fw[n]) if eligible else "UNIFORM"

    test={k:0 for k in BASE}; test[CAND[chosen]]=fra[chosen]
    # FRA base features come from existing target card pool, same definitions as prior model.
    base=fm.fra_table(target_path)
    test.update({k:base[k] for k in BASE})
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0));m.fit(df[feats(chosen)],df.turns)
    fp=float(m.predict(pd.DataFrame([test])[feats(chosen)])[0])

    # For comparison, predict FRA under all four weight schemes with otherwise identical model.
    fra_preds={}
    for name in CAND:
        z={k:base[k] for k in BASE};z[CAND[name]]=fra[name]
        mm=make_pipeline(StandardScaler(),Ridge(alpha=10.0));mm.fit(df[feats(name)],df.turns)
        fra_preds[name]=float(mm.predict(pd.DataFrame([z])[feats(name)])[0])

    errs=[]
    for s in df.set:
        tr=df[df.set.ne(s)];te=df[df.set.eq(s)]
        errs.append(float(te.turns.iloc[0])-float(pred(tr,te,chosen)[0]))
    ae=np.abs(errs)

    report={"external_holdouts_loaded":False,"fin_used":False,"mh3_used":False,"n_sets":21,"fra_cards":nfra,
      "weight_definition":{
        "GIH":"0.25 + 1.5 * predicted_GIH_percentile within set+rarity",
        "ALSA":"0.25 + 1.5 * (1 - predicted_ALSA_percentile) within set+rarity",
        "COMBINED":"sqrt(GIH_weight * ALSA_weight)"},
      "historical_predictions":"21-set OOF only; MH3 excluded from card-prediction training and speed training",
      "fixed_loso_mae":cv,"fixed_forward_mae":fw,
      "nested_loso":{"mae":om,"counts":oc,"folds":outer},"nested_forward":{"mae":nm,"counts":nc,"folds":nf},
      "eligible_vs_uniform":eligible,"chosen":chosen,
      "fra_engine_concentration":fra,"fra_predictions":fra_preds,"fra_pred":fp,
      "interval80":float(np.quantile(ae,.8,method="higher")),"interval90":float(np.quantile(ae,.9,method="higher"))}
    (out/"format_speed_playability_weighted.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    df.to_csv(out/"format_speed_playability_weighted_features.csv",index=False)
    cards[["set","name","pred_gih_oof","pred_alsa_oof"]].to_csv(out/"card_playability_oof.csv",index=False)
    print("SUMMARY",json.dumps({k:report[k] for k in ["fixed_loso_mae","fixed_forward_mae","nested_loso","nested_forward","eligible_vs_uniform","chosen","fra_engine_concentration","fra_predictions","fra_pred","interval80","interval90"]},ensure_ascii=False))
if __name__=="__main__":main(*sys.argv[1:6])
