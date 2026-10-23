"""N1 neighbour-residual correction (PLAN.md). Runs on lists from neighbors.mjs / lists_py.py. python3 -I n1.py"""
import json,warnings,sys
from pathlib import Path
import numpy as np,pandas as pd
warnings.filterwarnings('ignore')
W=Path('/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/')
HERE=Path(__file__).resolve().parent
oof=pd.read_csv(W/'17lands-limited-forecast-data/research/c9_power_questions/oof_B10.csv.gz')
oof['key']=oof.set+'|'+oof.name; assert oof.key.is_unique
oof['act']=oof.actual_gih*100; oof['p']=oof.pred*100
oof['r']=oof.act-oof.p; oof['r']-=oof.groupby('set').r.transform('mean')   # set-centred residual (pp)
R=dict(zip(oof.key,oof.r))
N=json.load(open(W/'work/n1_neighbors.json')); L3=json.load(open(W/'work/n1_lists_py.json'))
sets=sorted(oof.set.unique()); K=[3,5,10,20]; AL=[0,.1,.2,.3,.5,.75,1.0]
keys=oof.key.to_numpy(); st=oof.set.to_numpy(); n=len(oof)
def ranked(var,key):
    if var=='V1': return N[key]['ok'],N[key]['no']
    if var=='V2': return N[key]['old'],[]
    if var=='V3': return L3[key]['v3'],L3[key]['v3no']
    if var=='C0': return L3[key]['c0'],L3[key]['c0no']
def setof(k): return k.split('|',1)[0]
# M[var][k][e] : array n, weighted mean neighbour residual with neighbours from sets other than own set and other than e
def build_M(var):
    M={k:{e:np.zeros(n) for e in sets} for k in K}
    for i,key in enumerate(keys):
        a,b=ranked(var,key)
        for e in sets:
            ex=[x for x in a if setof(x[0])!=e]
            if len(ex)<20: ex=ex+[x for x in b if setof(x[0])!=e]
            for k in K:
                t=ex[:k]
                if var=='V1': w=[max(x[1],1e-3) for x in t]
                elif var=='V2': w=[max(x[1],1e-3) for x in t]
                elif var=='V3': w=[max(x[1],.01) for x in t]
                else: w=[1.0]*len(t)
                M[k][e][i]=np.average([R[x[0]] for x in t],weights=w)
    return M
# V4 tag-group
c5=pd.read_csv(W/'17lands-limited-forecast-data/research/c5_atomic_effects/c5_features.csv.gz'); c5=c5.drop_duplicates('key').set_index('key')
tags=[c for c in c5.columns if c.startswith('c5_') and len(c)==5]
T=(c5.reindex(keys)[tags].fillna(0).to_numpy()>0).astype(float)
def build_M4():
    SR=np.array([[ (T[st==s,j]*oof.r.to_numpy()[st==s]).sum() for j in range(len(tags))] for s in sets]); SN=np.array([T[st==s].sum(0) for s in sets])
    out={}
    for e in sets:
        out[e]=np.zeros(n)
        for t in sets:
            tr=[i for i,s in enumerate(sets) if s not in (t,e)]
            sr,sn=SR[tr].sum(0),SN[tr].sum(0); m=sr/(sn+20); m[sn<30]=np.nan
            idx=st==t; X=T[idx]; mm=np.where(X>0,m[None,:],np.nan)
            c=np.nanmean(mm,axis=1); out[e][idx]=np.nan_to_num(c)
    return out
def perset(p):
    d=oof.assign(p2=p); out={}
    for s,g in d.groupby('set'):
        e=(g.p2-g.act); top=g.act.rank(ascending=False,method='first')<=10; bot=g.act.rank(method='first')<=10; pr=g.p2.rank(ascending=False,method='first')
        out[s]=dict(t_bias=e[top].mean(),t_mae=e[top].abs().mean(),hit20=float((pr[top]<=20).mean()),b_bias=e[bot].mean(),f_bias=-e[pr<=10].mean(),mae=e.abs().mean(),n=len(g),sp=g.p2.corr(g.act,method='spearman'))
    return pd.DataFrame(out).T
def summ(ps): return dict(mae=(ps.mae*ps.n).sum()/ps.n.sum(),sp=ps.sp.mean(),t_bias=ps.t_bias.mean(),t_mae=ps.t_mae.mean(),hit20=ps.hit20.mean(),b_bias=ps.b_bias.mean(),f_bias=ps.f_bias.mean())
act=oof.act.to_numpy(); base=oof.p.to_numpy()
def nested(Mget,ks):
    """Mget(k,e)->array. returns outer corrected prediction and chosen params per set."""
    pred=base.copy(); chosen={}
    for s in sets:
        inner=st!=s; best=None
        for k in ks:
            Me=Mget(k,s)
            for a in AL:
                mae=np.abs(act[inner]-(base[inner]+a*Me[inner])).mean()
                key=(mae,a,k)
                if best is None or key<best: best=key
        _,a,k=best; chosen[s]=(k,a); idx=st==s; pred[idx]=base[idx]+a*Mget(k,s)[idx]
    return pred,chosen
res={}; preds={'B10':base}; chosen={}; M={}
for var in ['V1','V2','V3','C0']:
    M[var]=build_M(var); preds[var],chosen[var]=nested(lambda k,e,var=var:M[var][k][e],K); print(var,'done',flush=True)
M4=build_M4(); preds['V4'],chosen['V4']=nested(lambda k,e:M4[e],[0]); print('V4 done')
# non-nested oracle (own set excluded only): best (k,alpha) overall, descriptive
orc={}
def own(var,k): return np.array([M[var][k][st[i]][i] for i in range(n)])
for var in ['V1','V2','V3','C0']:
    best=min(((np.abs(act-(base+a*own(var,k))).mean(),k,a) for k in K for a in AL)); orc[var]=best
M4own=np.array([M4[st[i]][i] for i in range(n)]); orc['V4']=min(((np.abs(act-(base+a*M4own)).mean(),0,a) for a in AL))
PS={k:perset(p) for k,p in preds.items()}; S={k:summ(v) for k,v in PS.items()}
b=PS['B10']
rows=[]
for k in preds:
    s=S[k]; imp=int((PS[k].mae<b.mae-1e-12).sum())
    row=dict(variant=k,pooled_mae=s['mae'],d_mae=s['mae']-S['B10']['mae'],t_bias=s['t_bias'],t_mae=s['t_mae'],hit20=s['hit20'],spearman=s['sp'],b_bias=s['b_bias'],f_bias=s['f_bias'],sets_improved=imp)
    if k!='B10':
        row.update(a=S['B10']['mae']-s['mae']>=0.01, b=abs(s['t_bias'])<=abs(S['B10']['t_bias']), c=s['sp']>=S['B10']['sp'], d=imp>=15)
        row['pass']=all(row[x] for x in 'abcd')
    rows.append(row)
T1=pd.DataFrame(rows); T1.to_csv(HERE/'summary_by_variant.csv',index=False,float_format='%.4f')
pd.set_option('display.width',250); print(T1.round(4).to_string())
print('oracle (non-nested, descriptive):',{k:(round(v[0],4),v[1],v[2]) for k,v in orc.items()})
ch=pd.DataFrame({v:{s:f'k{chosen[v][s][0]}/a{chosen[v][s][1]}' for s in sets} for v in chosen}); ch.to_csv(HERE/'chosen_params.csv'); print(ch.T.to_string())
# per-set MAE table
pd.DataFrame({k:v.mae for k,v in PS.items()}).to_csv(HERE/'per_set_mae.csv',float_format='%.4f')
# rarity
rar=['common','uncommon','rare','mythic']; rr=[]
for k in preds:
    d=oof.assign(p2=preds[k]); d['e']=d.p2-d.act
    top=d.groupby('set').act.rank(ascending=False,method='first')<=10
    for r in range(4):
        g=d[d.rarity_ord==r]; rr.append(dict(variant=k,rarity=rar[r],n=len(g),mae=g.e.abs().mean(),mean_err=g.e.mean(),n_top10=int((top&(d.rarity_ord==r)).sum()),top10_mean_err=d[top&(d.rarity_ord==r)].e.mean()))
RR=pd.DataFrame(rr); RR.to_csv(HERE/'by_rarity.csv',index=False,float_format='%.4f'); print(RR.round(3).to_string())
# AN tag
an=(c5.reindex(keys)['c5_AN'].fillna(0).to_numpy()>0)
print('AN cards',an.sum(),{k:round(float((preds[k][an]-act[an]).mean()),3) for k in preds})
# named
nm=[('MSH','Avengers Assemble!'),('ECL','Chronicle of Victory')]; rows=[]
for s,name in nm:
    i=int(np.flatnonzero((oof.set==s)&(oof.name==name))[0]); idx=np.flatnonzero(st==s)
    row=dict(card=name,set=s,actual=act[i],actual_rank=int((act[idx]>act[i]).sum()+1))
    for k in preds: row[k]=round(float(preds[k][i]),2); row[k+'_rank']=int((preds[k][idx]>preds[k][i]).sum()+1)
    rows.append(row)
NM=pd.DataFrame(rows); NM.to_csv(HERE/'named_cards.csv',index=False); print(NM.T.to_string())
# neighbours of the named cards (names only, for the report)
for s,name in nm:
    key=f'{s}|{name}'
    for v in ('V1','V2','V3'):
        a,_=ranked(v,key); print(key,v,[(x[0],round(R[x[0]],1)) for x in a[:5]],'M(k5)=',round(float(M[v][5][s][int(np.flatnonzero(keys==key)[0])]),2))
json.dump({'summary':T1.to_dict('records'),'oracle':{k:list(map(float,v)) for k,v in orc.items()}},open(HERE/'result.json','w'),indent=1,default=float)
