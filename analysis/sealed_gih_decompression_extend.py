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
BLENDS=[0.5,0.6,0.7]
DECOMP=[1.25,1.4,1.55,1.7]

def main(feature_csv,actual_csv,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(feature_csv);a=pd.read_csv(actual_csv)
    if any("FIN" in set(x.set.astype(str).str.upper()) for x in [f,a]):raise SystemExit("FIN guard")
    d=f[f.set.isin(SETS)].merge(a,on=["set","name"],how="inner").reset_index(drop=True)
    cols=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
    txt=d.oracle_text.fillna("")+" TYPE "+d.type_line.fillna("")
    cand=list(itertools.product(BLENDS,DECOMP))
    pred={c:np.full(len(d),np.nan) for c in cand}
    for hold in SETS:
        tr=d.set.ne(hold);te=~tr
        imp=SimpleImputer(strategy="median");Xtr=imp.fit_transform(d.loc[tr,cols]);Xte=imp.transform(d.loc[te,cols])
        tree=ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922)
        tree.fit(Xtr,d.loc[tr,"sealed_gih"]);pt=tree.predict(Xte)
        v=TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True)
        A=v.fit_transform(txt[tr]);B=v.transform(txt[te])
        rr=Ridge(alpha=10);rr.fit(A,d.loc[tr,"sealed_gih"]);px=rr.predict(B)
        center=float(d.loc[tr,"sealed_gih"].mean())
        for b,z in cand:
            raw=b*pt+(1-b)*px
            pred[(b,z)][te]=center+z*(raw-center)
        print("FOLD",hold)
    y=d.sealed_gih.to_numpy(float);rows=[]
    for (b,z),p in pred.items():
        ae=np.abs(y-p)
        folds=[]
        for s,g in d.assign(_p=p).groupby("set"):
            folds.append(float(np.mean(np.abs(g.sealed_gih-g._p))*100))
        # Extreme decile bias, using held-out predictions only.
        lo=np.quantile(y,.1);hi=np.quantile(y,.9)
        rows.append({"blend_struct":b,"decomp":z,"mae_pp":float(ae.mean()*100),
          "weighted_mae_pp":float(np.average(ae,weights=np.sqrt(d.sealed_gih_count))*100),
          "spearman":float(spearmanr(y,p).statistic),"macro_set_mae_pp":float(np.mean(folds)),
          "sets_below_base":0,
          "low10_bias_pp":float(np.mean(p[y<=lo]-y[y<=lo])*100),
          "high10_bias_pp":float(np.mean(p[y>=hi]-y[y>=hi])*100)})
    res=pd.DataFrame(rows)
    base=res[(res.blend_struct==.7)&(res.decomp==1.25)].iloc[0]
    # recompute set wins vs base
    bp=pred[(.7,1.25)]
    for i,r in res.iterrows():
        p=pred[(r.blend_struct,r.decomp)]
        wins=0
        for s in SETS:
            ix=d.set.eq(s).to_numpy()
            if np.mean(np.abs(y[ix]-p[ix])) < np.mean(np.abs(y[ix]-bp[ix])):wins+=1
        res.loc[i,"sets_below_base"]=wins
    res=res.sort_values("mae_pp")
    res.to_csv(out/"sealed_gih_decompression_results.csv",index=False)
    rep={"fin_used":False,"mh3_used":False,"base":base.to_dict(),"results":res.to_dict("records")}
    (out/"sealed_gih_decompression_report.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"base":rep["base"],"top":rep["results"][:10]}))
if __name__=="__main__":main(*sys.argv[1:4])
