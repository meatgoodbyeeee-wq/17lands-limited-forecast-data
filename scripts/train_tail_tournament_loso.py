#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import mean_absolute_error
REQ={"set","name","actual_gih"}
def norm(x):
 x=pd.to_numeric(x,errors="coerce"); return x/100 if x.dropna().median()>1.5 else x
def met(d,col,k=30):
 d=d.dropna(subset=["actual_gih",col]); y=d.actual_gih.to_numpy();p=d[col].to_numpy();kk=min(k,len(d))
 at=set(np.argsort(-y)[:kk]);pt=set(np.argsort(-p)[:kk]);ab=set(np.argsort(y)[:kk]);pb=set(np.argsort(p)[:kk])
 return {"n":len(d),"mae_pp":mean_absolute_error(y,p)*100,"spearman":float(spearmanr(y,p).statistic),"top30":len(at&pt)/kk,"bottom30":len(ab&pb)/kk}
def pairs(d,fs,tail=.20,gap=.25,cap=9000,seed=20260922):
 rng=np.random.default_rng(seed);xx=[];yy=[];ww=[]
 for _,g in d.groupby("set"):
  g=g.dropna(subset=["actual_gih"]).copy();g[fs]=g[fs].replace([np.inf,-np.inf],np.nan);g[fs]=g[fs].fillna(g[fs].median(numeric_only=True)).fillna(0);g["q"]=g.actual_gih.rank(pct=True);X=g[fs].to_numpy(float);q=g.q.to_numpy();y=g.actual_gih.to_numpy();cand=[]
  for i in range(len(g)):
   for j in range(i+1,len(g)):
    gp=abs(q[i]-q[j]); lowi=q[i]<=tail; lowj=q[j]<=tail; highi=q[i]>=1-tail; highj=q[j]>=1-tail
    if gp>=gap and (lowi or lowj or highi or highj):
     # Bottom-tail mistakes are the current weakness: emphasize comparisons containing a weak card.
     bottom=int(lowi)+int(lowj); top=int(highi)+int(highj); cand.append((i,j,gp,bottom,top))
  if len(cand)>cap:cand=[cand[z] for z in rng.choice(len(cand),cap,replace=False)]
  for i,j,gp,nb,nt in cand:
   z=X[i]-X[j];lab=int(y[i]>y[j]);xx += [z,-z];yy += [lab,1-lab];ww += [gp*(1+1.75*nb+0.5*nt)]*2
 return np.asarray(xx),np.asarray(yy),np.asarray(ww)
def fit(d,fs):
 X,y,w=pairs(d,fs);m=HistGradientBoostingClassifier(learning_rate=.05,max_iter=180,max_leaf_nodes=15,l2_regularization=1,random_state=20260922);m.fit(X,y,sample_weight=w);return m
def score(m,d,fs):
 out=pd.Series(np.nan,index=d.index)
 for _,ix in d.groupby("set").groups.items():
  ix=list(ix);X=d.loc[ix,fs].replace([np.inf,-np.inf],np.nan).copy();X=X.fillna(X.median(numeric_only=True)).fillna(0).to_numpy(float);pos=np.arange(len(X))
  if len(X)<2:continue
  sc=[]
  for i in range(len(X)):
   mask=np.arange(len(X))!=i;sc.append(m.predict_proba(X[i]-X[mask])[:,1].mean())
  out.loc[list(np.asarray(ix,dtype=object)[pos])]=sc
 return out.to_numpy()
def main():
 a=argparse.ArgumentParser();a.add_argument("--input",type=Path,required=True);a.add_argument("--out",type=Path,required=True);z=a.parse_args();d=pd.read_csv(z.input);assert REQ<=set(d);d["set"]=d["set"].str.upper();assert "FIN" not in set(d["set"]);d.actual_gih=norm(d.actual_gih)
 fs=[c for c in d.select_dtypes(include=[np.number]).columns if c not in {"actual_gih","gih_games","gih_wins","gih_wr_pct"} and not c.startswith("color_")]
 # Recreate the exact FIN-blind 1.25x text+structured base used by the main model.
 from sklearn.ensemble import ExtraTreesRegressor
 from sklearn.impute import SimpleImputer
 from sklearn.pipeline import make_pipeline
 from sklearn.feature_extraction.text import TfidfVectorizer
 from sklearn.linear_model import Ridge
 base=np.full(len(d),np.nan)
 txt=d["oracle_text"].fillna("")+" TYPE "+d["type_line"].fillna("")
 for hold in sorted(d["set"].unique()):
  tr=d.set!=hold;te=d.set==hold
  m0=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=12,max_features=.8,n_jobs=-1,random_state=20260922))
  m0.fit(d.loc[tr,fs],d.loc[tr,"actual_gih"]);pt=m0.predict(d.loc[te,fs])
  mt=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=20))
  mt.fit(txt[tr],d.loc[tr,"actual_gih"]);px=mt.predict(txt[te])
  raw=.7*pt+.3*px;center=float(d.loc[tr,"actual_gih"].mean());base[te]=center+1.25*(raw-center)
 d["base_pred"]=base
 pred=np.full(len(d),np.nan); folds={}
 for hold in sorted(d["set"].unique()):
  tr=d.set!=hold;te=d.set==hold;m=fit(d.loc[tr],fs);s=score(m,d.loc[te],fs);tmp=d.loc[te].copy();tmp["rank"]=s
  # rank score -> residual mapping trained only on the four training sets via direct tournament scores
  st=score(m,d.loc[tr],fs);cal=d.loc[tr].copy();cal["rank"]=st;x=cal["rank"].to_numpy();y=(cal.actual_gih-cal.base_pred).to_numpy();ok=np.isfinite(x)&np.isfinite(y);A=np.c_[np.ones(ok.sum()),x[ok]-.5];coef=np.linalg.lstsq(A,y[ok],rcond=None)[0]
  delta=coef[0]+coef[1]*(s-.5);conf=np.clip(abs(s-.5)*2,0,1);# Use tournament score as a rank feature, not a direct value correction.
  # Blend percentile ranks only; convert back to base-prediction values so calibration stays anchored.
  bp=tmp.base_pred.to_numpy(); br=pd.Series(bp).rank(pct=True).to_numpy(); rr=pd.Series(s).rank(pct=True).to_numpy()
  mix=.85*br+.15*rr
  order=np.argsort(bp); sorted_bp=np.sort(bp); q=np.clip(mix,1/len(bp),1)
  p=np.quantile(sorted_bp,q,method="linear")
  pred[te]=p;tmp["tail_pred"]=p;folds[hold]=met(tmp,"tail_pred")
 d["tail_pred"]=pred;out={"fin_used":False,"scoring":"bottom_tail_weighted_pairwise_15pct_experiment","folds":folds,"overall":met(d,"tail_pred")};z.out.parent.mkdir(parents=True,exist_ok=True);z.out.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=="__main__":main()

