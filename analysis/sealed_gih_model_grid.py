#!/usr/bin/env python3
import sys,json,itertools
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge

SETS=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number",
      "sealed_gih","sealed_gih_count","sealed_gih_wins"}
LEAVES=[8,16]
BLENDS=[0.6,0.7,0.8]
DECOMP=[1.0,1.15,1.25]
TARGETS=["RAW","SHRINK500"]

def numeric(d):
    return [c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]

def target(train,kind):
    y=train.sealed_gih.to_numpy(float)
    if kind=="RAW": return y
    prior=train.groupby("rarity_ord").sealed_gih.transform("mean").to_numpy(float)
    n=train.sealed_gih_count.to_numpy(float)
    k=500.0
    return (n*y+k*prior)/(n+k)

def main(feature_csv,actual_csv,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_csv);a=pd.read_csv(actual_csv)
    if any("FIN" in set(x.set.astype(str).str.upper()) for x in [f,a]):raise SystemExit("FIN guard")
    d=f[f.set.isin(SETS)].merge(a,on=["set","name"],how="inner").reset_index(drop=True)
    cols=numeric(d); txt=d.oracle_text.fillna("")+" TYPE "+d.type_line.fillna("")
    cand=[(t,l,b,z) for t in TARGETS for l in LEAVES for b in BLENDS for z in DECOMP]
    pred={c:np.full(len(d),np.nan) for c in cand}
    for hold in SETS:
        tr=d.set.ne(hold);te=~tr
        imp=SimpleImputer(strategy="median")
        Xtr=imp.fit_transform(d.loc[tr,cols]);Xte=imp.transform(d.loc[te,cols])
        vec=TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True)
        A=vec.fit_transform(txt[tr]);B=vec.transform(txt[te])
        for tk in TARGETS:
            y=target(d.loc[tr],tk)
            text=Ridge(alpha=10);text.fit(A,y);ptxt=text.predict(B)
            trees={}
            for leaf in LEAVES:
                m=ExtraTreesRegressor(n_estimators=600,min_samples_leaf=leaf,max_features=.6,n_jobs=-1,random_state=20260922)
                m.fit(Xtr,y);trees[leaf]=m.predict(Xte)
            center=float(np.mean(y))
            for leaf,b,z in itertools.product(LEAVES,BLENDS,DECOMP):
                raw=b*trees[leaf]+(1-b)*ptxt
                pred[(tk,leaf,b,z)][te]=center+z*(raw-center)
        print("FOLD",hold)

    y=d.sealed_gih.to_numpy(float)
    rows=[]
    foldrows=[]
    last5=set(SETS[-5:])
    for c,p in pred.items():
        tk,leaf,b,z=c
        ae=np.abs(y-p)
        sps=[];better=0
        for s,g in d.assign(_p=p).groupby("set"):
            idx=g.index.to_numpy()
            sps.append(float(spearmanr(g.sealed_gih,g._p).statistic))
        rows.append({"target":tk,"leaf":leaf,"blend_struct":b,"decomp":z,
          "mae_pp":float(ae.mean()*100),
          "sqrt_count_weighted_mae_pp":float(np.average(ae,weights=np.sqrt(d.sealed_gih_count))*100),
          "spearman":float(spearmanr(y,p).statistic),"macro_set_spearman":float(np.mean(sps)),
          "last5_mae_pp":float(ae[d.set.isin(last5)].mean()*100)})
    res=pd.DataFrame(rows).sort_values(["mae_pp","spearman"],ascending=[True,False])
    base=res[(res.target=="RAW")&(res.leaf==8)&(res.blend_struct==.7)&(res.decomp==1.25)].iloc[0]
    # Robust shortlist: improve total MAE and last5 MAE, without losing >.005 global Spearman.
    robust=res[(res.mae_pp<base.mae_pp)&(res.last5_mae_pp<base.last5_mae_pp)&(res.spearman>=base.spearman-.005)].copy()
    res.to_csv(out/"sealed_gih_grid_results.csv",index=False)
    rep={"fin_used":False,"mh3_used":False,"sets":SETS,
      "base":base.to_dict(),"top10":res.head(10).to_dict("records"),"robust":robust.head(15).to_dict("records"),
      "grid":{"targets":TARGETS,"leaves":LEAVES,"blends":BLENDS,"decomp":DECOMP},
      "note":"Grid is diagnostic fixed-candidate LOSO, not nested hyperparameter selection. A candidate must show a material/stable gain before a nested confirmation run."}
    (out/"sealed_gih_grid_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"base":rep["base"],"top10":rep["top10"],"robust":rep["robust"][:10]}))
if __name__=="__main__":main(*sys.argv[1:4])
