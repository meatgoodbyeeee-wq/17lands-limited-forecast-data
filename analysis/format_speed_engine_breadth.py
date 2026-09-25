#!/usr/bin/env python3
import sys,json,gzip,re,urllib.request
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
sys.path.insert(0,"analysis")
import format_speed_mechanism_effects as fm

BASE=fm.BASE
ALL22={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
PAIRS=fm.PAIRS

def pair_engine_metrics(flags, colors):
    vals=[]
    for pair,cs in PAIRS.items():
        idx=[i for i,col in enumerate(colors) if col and col.issubset(cs)]
        vals.append(float(np.mean([flags[i]["engine"] for i in idx])) if idx else 0.0)
    a=np.asarray(vals,float)
    mx=float(a.max()); mn=float(a.min()); mean=float(a.mean()); sd=float(a.std())
    if a.sum()>0:
        p=a/a.sum()
        ent=float(-(p[p>0]*np.log(p[p>0])).sum()/np.log(len(a)))
    else: ent=0.0
    return {
      "engine_pair_mean10":mean,
      "engine_pair_sd10":sd,
      "engine_pair_cv10":sd/(mean+1e-9),
      "engine_pair_min10":mn,
      "engine_breadth_meanmax":mean/(mx+1e-9),
      "engine_breadth_minmax":mn/(mx+1e-9),
      "engine_breadth_entropy":ent,
      "engine_breadth_top75":float(np.mean(a >= 0.75*mx)) if mx>0 else 0.0,
      "engine_pairmax_raw":mx,
      "engine_pair_values":vals,
    }

def hist_table(path):
    d=pd.read_csv(path)
    sets=set(d["set"].astype(str).str.upper())
    if "FIN" in sets or sets!=ALL22: raise SystemExit("FIN/set guard failed")
    d=d[d["set"].ne("MH3") & d["rarity_ord"].isin([0,1]) & d["type_land"].eq(0)].copy()
    tar=fm.targets(); rows=[]
    for s,g in d.groupby("set"):
        cr=g[g.type_creature.eq(1)]
        flags=[fm.text_flags(str(r.oracle_text or ""),r.power,bool(r.type_planeswalker)) for _,r in g.iterrows()]
        colors=fm.card_colors_from_hist(g)
        m=pair_engine_metrics(flags,colors)
        row={"set":s,"start_date":pd.to_datetime(g.window_start.iloc[0]),"turns":tar[s],
             "mean_mv":float(g.mv.mean()),"cheap_creature_share":float((cr.mv<=2).mean()) if len(cr) else 0,
             "cheap_interaction_share":float(g.cheap_interaction.mean()),"card_advantage_share":float(g.card_advantage.mean()),
             "evasion_share":float(g.evasion.mean()),
             "engine_global":float(np.mean([x["engine"] for x in flags])),
             "engine_pairmax":m["engine_pairmax_raw"]}
        row["engine_concentration"]=row["engine_pairmax"]-row["engine_global"]
        row.update({k:v for k,v in m.items() if k!="engine_pair_values"})
        rows.append(row)
    return pd.DataFrame(rows)

def fra_table(path):
    with gzip.open(path,"rt",encoding="utf-8") as f: root=json.load(f)
    cards=root.get("cards") or root.get("forecast",{}).get("cards") or root.get("target",{}).get("cards")
    use=[c for c in cards if c.get("rarity") in {"common","uncommon"} and "land" not in (c.get("type_line") or "").lower()]
    vals=[];flags=[];colors=[]
    for c in use:
        t=(c.get("oracle_text") or "").lower();typ=(c.get("type_line") or "").lower();mv=float(c.get("cmc",c.get("mv",0)) or 0)
        creature=int("creature" in typ)
        interaction=int(bool(re.search(r"destroy target|exile target|target creature gets -|deals? [^.]*damage to (any target|target creature|target permanent)|return target .* to (its|their) owner.?s hand",t)))
        ca=int(bool(re.search(r"draw (two|three|x|that many) cards",t)) or ("create" in t and "token" in t and ("enters" in t or "enter the battlefield" in t)))
        ev=int(any(x in t for x in ["flying","menace","can't be blocked","cannot be blocked"]))
        vals.append((mv,creature,int(interaction and mv<=3),ca,ev))
        try:p=float(c.get("power"))
        except:p=0.0
        flags.append(fm.text_flags(t,p,"planeswalker" in typ))
        colors.append(set(c.get("colors") or []))
    a=np.array(vals,float);cr=a[a[:,1]==1]
    m=pair_engine_metrics(flags,colors)
    row={"mean_mv":float(a[:,0].mean()),"cheap_creature_share":float((cr[:,0]<=2).mean()),
         "cheap_interaction_share":float(a[:,2].mean()),"card_advantage_share":float(a[:,3].mean()),
         "evasion_share":float(a[:,4].mean()),
         "engine_global":float(np.mean([x["engine"] for x in flags])),
         "engine_pairmax":m["engine_pairmax_raw"]}
    row["engine_concentration"]=row["engine_pairmax"]-row["engine_global"]
    row.update({k:v for k,v in m.items() if k!="engine_pair_values"})
    row["engine_pair_values"]=m["engine_pair_values"]
    return row

CAND={
 "BASE":[],
 "CONCENTRATION":["engine_concentration"],
 "BREADTH_MEANMAX":["engine_breadth_meanmax"],
 "BREADTH_ENTROPY":["engine_breadth_entropy"],
 "BREADTH_TOP75":["engine_breadth_top75"],
 "BREADTH_MINMAX":["engine_breadth_minmax"],
 "PAIR_MEAN10":["engine_pair_mean10"],
 "PAIR_SD10":["engine_pair_sd10"],
 # concentration + breadth allows level and spread to separate, but only 2 extra dfs.
 "CONC_PLUS_ENTROPY":["engine_concentration","engine_breadth_entropy"],
 "CONC_PLUS_MEANMAX":["engine_concentration","engine_breadth_meanmax"],
}
def feats(n):return BASE+CAND[n]
def pred(tr,te,n):
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0));m.fit(tr[feats(n)],tr.turns)
    return m.predict(te[feats(n)])
def loo(df,n):
    e=[]
    for s in df.set:
        tr=df[df.set.ne(s)];te=df[df.set.eq(s)]
        e.append(abs(float(te.turns.iloc[0])-float(pred(tr,te,n)[0])))
    return float(np.mean(e))
def forward(df,n,min_train=8):
    d=df.sort_values("start_date").reset_index(drop=True);e=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i];te=d.iloc[[i]]
        e.append(abs(float(te.turns.iloc[0])-float(pred(tr,te,n)[0])))
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

def main(dev_csv,fra_gz,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    df=hist_table(dev_csv);fra=fra_table(fra_gz)
    if len(df)!=21 or "FIN" in set(df.set) or "MH3" in set(df.set):raise SystemExit("guard")
    cv={n:loo(df,n) for n in CAND};fw={n:forward(df,n) for n in CAND}
    outer=nested(df);nf=nested_forward(df)
    om=float(np.mean([x["abs_err"] for x in outer])); fmw=float(np.mean([x["abs_err"] for x in nf]))
    oc={n:sum(x["selected"]==n for x in outer) for n in CAND}
    fc={n:sum(x["selected"]==n for x in nf) for n in CAND}
    eligible=[n for n in CAND if cv[n]<cv["BASE"] and fw[n]<fw["BASE"]]
    chosen=min(eligible,key=lambda n:cv[n]+fw[n]) if eligible else "BASE"
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0));m.fit(df[feats(chosen)],df.turns)
    fp=float(m.predict(pd.DataFrame([fra])[feats(chosen)])[0])
    coefs=[]
    if chosen!="BASE":
      for s in df.set:
        tr=df[df.set.ne(s)]
        mm=make_pipeline(StandardScaler(),Ridge(alpha=10.0));mm.fit(tr[feats(chosen)],tr.turns)
        coefs.append(mm.named_steps["ridge"].coef_[-len(CAND[chosen]):].tolist())
    errs=[]
    for s in df.set:
        tr=df[df.set.ne(s)];te=df[df.set.eq(s)]
        errs.append(float(te.turns.iloc[0])-float(pred(tr,te,chosen)[0]))
    ae=np.abs(errs)
    report={"external_holdouts_loaded":False,"fin_used":False,"mh3_used":False,
      "fixed_loso_mae":cv,"fixed_forward_mae":fw,
      "nested_loso":{"mae":om,"counts":oc,"folds":outer},"nested_forward":{"mae":fmw,"counts":fc,"folds":nf},
      "eligible_both":eligible,"chosen":chosen,"fra_pred":fp,
      "fra_engine":{"global":fra["engine_global"],"pairmax":fra["engine_pairmax"],"concentration":fra["engine_concentration"],
                    "mean10":fra["engine_pair_mean10"],"sd10":fra["engine_pair_sd10"],"meanmax":fra["engine_breadth_meanmax"],
                    "entropy":fra["engine_breadth_entropy"],"top75":fra["engine_breadth_top75"],"minmax":fra["engine_breadth_minmax"],
                    "pair_values":fra["engine_pair_values"]},
      "coef_samples":coefs,
      "interval80":float(np.quantile(ae,.8,method="higher")),"interval90":float(np.quantile(ae,.9,method="higher"))}
    (out/"format_speed_engine_breadth.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    df.to_csv(out/"format_speed_engine_breadth_features.csv",index=False)
    print("SUMMARY",json.dumps({k:report[k] for k in ["fixed_loso_mae","fixed_forward_mae","nested_loso","nested_forward","eligible_both","chosen","fra_pred","fra_engine","interval80","interval90"]},ensure_ascii=False))
if __name__=="__main__":main(sys.argv[1],sys.argv[2],sys.argv[3])
