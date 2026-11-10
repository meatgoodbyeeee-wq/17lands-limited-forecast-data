import json, numpy as np, pandas as pd
R='/home/claude/17lands-limited-forecast-data/research/'
a=pd.read_csv(R+'c9_power_questions/oof_B10.csv.gz'); b=pd.read_csv(R+'g3_retrain/oof_B11g.csv.gz')
assert len(a)==len(b)==7075 and (a.set==b.set).all() and (a.name==b.name).all()
assert np.allclose(a.actual_gih,b.actual_gih)
models={'B10':a.pred.values*100,'B11g':b.pred.values*100,'AVG':(a.pred.values+b.pred.values)/2*100}
act=a.actual_gih.values*100; sets=a.set.values
res={}
for m,p in models.items():
    per={}
    for s in pd.unique(sets):
        i=np.where(sets==s)[0]; y=act[i]; q=p[i]; yc=y-y.mean(); qc=q-q.mean()
        r=np.corrcoef(q,y)[0,1]; beta=(qc@yc)/(yc@yc); cal=(qc@yc)/(qc@qc)
        top=np.argsort(-y,kind='stable')[:10]; D=yc[top].mean()
        uc=(yc-qc)[top].mean(); ur=(y-q)[top].mean()
        n=max(1,len(i)//10); tp=np.argsort(-q,kind='stable')[:n]
        t20=set(np.argsort(-q,kind='stable')[:20])
        per[s]=dict(n=len(i),r=r,beta=beta,slope_cal=cal,D=D,under_centred=uc,under_raw=ur,offset=y.mean()-q.mean(),
            inevitable=(1-r**2)*D,compression=(r**2-beta)*D,one_minus_beta_D=(1-beta)*D,gap_abs=abs(uc-(1-beta)*D),
            top10pct_bias=(y-q)[tp].mean(),hits=len(set(top)&t20))
    df=pd.DataFrame(per).T
    res[m]={'mean28':df.mean().to_dict(),'per_set':df.to_dict('index')}
json.dump(res,open('result_q1.json','w'),indent=1)
t=pd.DataFrame({m:res[m]['mean28'] for m in res}).drop('n'); print(t.round(3).to_string())
