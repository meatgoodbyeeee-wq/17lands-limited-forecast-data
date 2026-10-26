import numpy as np, pandas as pd
from prep import *
c,X,v=load()
o=pd.read_csv(C9/'oof_B10.csv.gz'); o['key']=o.set+'|'+o.name
# one row per unique card id, but sets matter: expand
rows=[]
for i,r in enumerate(c.itertuples()):
    for k in r.keys.split(';'): rows.append((k,i))
m=pd.DataFrame(rows,columns=['key','ci']); o=o.merge(m,on='key'); o=o.merge(c[['cat','mv','ntok']],left_on='ci',right_index=True)
print(len(o)); print(o.cat.value_counts().to_dict()); print('ntok quantiles',o.ntok.quantile([.1,.25,.5,.75]).tolist())
S=(X[o.ci.to_numpy()]@X[o.ci.to_numpy()].T).tocsr() if False else None
Xo=X[o.ci.to_numpy()]; sim=(Xo@Xo.T).toarray()
st=o["set"].to_numpy().astype(object); same=st[:,None]==st[None,:]
catm=(lambda a:a[:,None]==a[None,:])(o.cat.to_numpy().astype(object)); mvm=np.abs(o.mv.to_numpy()[:,None]-o.mv.to_numpy()[None,:])<=1
nm=(lambda a:a[:,None]!=a[None,:])(o["name"].to_numpy().astype(object))
for minTok in (0,6):
    tk=(o.ntok.to_numpy()>=minTok); tkm=tk[:,None]&tk[None,:]
    for th in (.95,.9,.85,.8,.75,.7,.6):
        ok=(sim>=th)&~same&catm&mvm&tkm
        okn=ok&nm
        print(minTok,th,'cards any(diff-name)',int(okn.any(1).sum()),'pairs',int(np.triu(okn|okn.T).sum()),'| incl same-name cards',int(ok.any(1).sum()))
