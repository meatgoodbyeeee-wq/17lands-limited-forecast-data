#!/usr/bin/env python3
import sys,json,tempfile,urllib.request,urllib.parse,urllib.error,time
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
sys.path.insert(0,"scripts")
from build_dev_features import card_features

TRAIN=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
EXT=["TMT","SOS","MSH","HOB"]
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number",
      "sealed_gih","sealed_gih_count","sealed_gih_wins"}

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"LimitedForecastResearch/5.0","Accept":"application/json"})
    for k in range(8):
        try:
            with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code!=429 or k==7:raise
            time.sleep(min(2**k,20))

def fetch_cards(s):
    url="https://api.scryfall.com/cards/search?q="+urllib.parse.quote(f"e:{s.lower()}")
    out=[]
    while url:
        d=get_json(url)
        for c in d["data"]:
            if c.get("digital") and "arena" not in c.get("games",[]):continue
            out.append(card_features(c))
        url=d.get("next_page") if d.get("has_more") else None
        time.sleep(.08)
    return pd.DataFrame(out).drop_duplicates("name")

def aggregate_set(s):
    url=f"https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{s}.Sealed.csv.gz"
    fn=Path(tempfile.gettempdir())/f"{s}.Sealed.csv.gz";urllib.request.urlretrieve(url,fn)
    hdr=pd.read_csv(fn,nrows=0).columns.tolist()
    tc="game_time" if "game_time" in hdr else ("draft_time" if "draft_time" in hdr else None)
    if not tc:raise RuntimeError(f"{s}: no time column")
    oh=[c for c in hdr if c.startswith("opening_hand_")]
    dr={c[len("drawn_"):]:c for c in hdr if c.startswith("drawn_")}
    names=[c[len("opening_hand_"):] for c in oh if c[len("opening_hand_"):] in dr]
    use=[tc,"won"]+[f"opening_hand_{n}" for n in names]+[dr[n] for n in names]
    # First pass only time column to define release-like 28d window.
    times=[]
    for ch in pd.read_csv(fn,usecols=[tc],chunksize=50000):
        x=pd.to_datetime(ch[tc],utc=True,errors="coerce").dropna()
        if len(x):times.append(x.min())
    start=min(times);end=start+pd.Timedelta(days=28)
    cnt={n:0.0 for n in names};wins={n:0.0 for n in names};ng=0
    for ch in pd.read_csv(fn,usecols=use,chunksize=1500,low_memory=False):
        gt=pd.to_datetime(ch[tc],utc=True,errors="coerce")
        ch=ch[(gt>=start)&(gt<end)]
        if ch.empty:continue
        ng+=len(ch);w=pd.to_numeric(ch.won,errors="coerce").fillna(0).to_numpy(float)
        for n in names:
            x=pd.to_numeric(ch[f"opening_hand_{n}"],errors="coerce").fillna(0).to_numpy(float)+pd.to_numeric(ch[dr[n]],errors="coerce").fillna(0).to_numpy(float)
            if x.sum():
                cnt[n]+=float(x.sum());wins[n]+=float((x*w).sum())
    fn.unlink(missing_ok=True)
    actual=pd.DataFrame([{"set":s,"name":n,"sealed_gih_count":cnt[n],"sealed_gih_wins":wins[n],"sealed_gih":wins[n]/cnt[n]}
                         for n in names if cnt[n]>=30])
    feat=fetch_cards(s);m=actual.merge(feat,on="name",how="inner")
    m["window_start"]=str(start);m["window_end"]=str(end)
    m["is_supplemental_power_set"]=0;m["is_premier_set"]=1
    return m,{"start":str(start),"end":str(end),"games":ng,"actual_cards":len(actual),"merged_cards":len(m)}

def main(feature_csv,actual_csv,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_csv);a=pd.read_csv(actual_csv)
    if any("FIN" in set(x.set.astype(str).str.upper()) for x in [f,a]):raise SystemExit("FIN guard")
    tr=f[f.set.isin(TRAIN)].merge(a,on=["set","name"],how="inner").reset_index(drop=True)
    cols=[c for c in tr.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(tr[c])]
    imp=SimpleImputer(strategy="median");X=imp.fit_transform(tr[cols])
    tree=ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922)
    tree.fit(X,tr.sealed_gih)
    txt=tr.oracle_text.fillna("")+" TYPE "+tr.type_line.fillna("")
    vec=TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True);A=vec.fit_transform(txt)
    rr=Ridge(alpha=10);rr.fit(A,tr.sealed_gih)
    center=float(tr.sealed_gih.mean())
    allrows=[];meta={}
    for s in EXT:
        q,md=aggregate_set(s)
        for c in cols:
            if c not in q:q[c]=np.nan
        raw=.7*tree.predict(imp.transform(q[cols]))+.3*rr.predict(vec.transform(q.oracle_text.fillna("")+" TYPE "+q.type_line.fillna("")))
        q["pred"]=center+1.25*(raw-center);q["ae"]=abs(q.sealed_gih-q.pred)
        allrows.append(q);meta[s]=md
        print("EXT_DONE",s,json.dumps(md))
    z=pd.concat(allrows,ignore_index=True)
    per={}
    for s,g in z.groupby("set"):
        per[s]={"n":len(g),"mae_pp":float(g.ae.mean()*100),
          "sqrt_weighted_mae_pp":float(np.average(g.ae,weights=np.sqrt(g.sealed_gih_count))*100),
          "spearman":float(spearmanr(g.sealed_gih,g.pred).statistic),
          "bias_pp":float((g.pred-g.sealed_gih).mean()*100)}
    rarity={}
    for r,g in z.groupby("rarity_ord"):
        rarity[str(int(r))]={"n":len(g),"mae_pp":float(g.ae.mean()*100),"spearman":float(spearmanr(g.sealed_gih,g.pred).statistic)}
    thresholds={}
    for t in [30,100,300,1000]:
        g=z[z.sealed_gih_count>=t]
        thresholds[str(t)]={"n":len(g),"mae_pp":float(g.ae.mean()*100),"spearman":float(spearmanr(g.sealed_gih,g.pred).statistic)}
    rep={"fin_used":False,"mh3_used":False,"training_sets":TRAIN,"external_sets":EXT,"metadata":meta,
      "overall":{"n":len(z),"mae_pp":float(z.ae.mean()*100),
        "sqrt_weighted_mae_pp":float(np.average(z.ae,weights=np.sqrt(z.sealed_gih_count))*100),
        "spearman":float(spearmanr(z.sealed_gih,z.pred).statistic)},
      "per_set":per,"rarity":rarity,"thresholds":thresholds}
    z[["set","name","rarity_ord","sealed_gih_count","sealed_gih","pred","ae"]].to_csv(out/"sealed_gih_external_predictions.csv",index=False)
    (out/"sealed_gih_external_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(rep))
if __name__=="__main__":main(*sys.argv[1:4])
