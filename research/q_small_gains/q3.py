import sys, json, gzip, numpy as np, pandas as pd
from scipy.stats import spearmanr
R='/home/claude/17lands-limited-forecast-data/'
sys.path.insert(0,R+'research/c9_power_questions'); sys.path.insert(0,R+'research/c5_atomic_effects')
sys.argv,_a=['c9'],sys.argv
import c9
sys.argv=_a
pool,base,cols=c9.load_pool()
o=pd.read_csv(R+'research/g3_retrain/oof_B11g.csv.gz'); o10=pd.read_csv(R+'research/c9_power_questions/oof_B10.csv.gz')
assert len(pool)==len(o)==7075 and (pool.set.values==o.set.values).all() and (pool.name.values==o.name.values).all()
ORDER='KHM STX AFR MID VOW NEO SNC DMU BRO ONE MOM LTR WOE LCI MKM OTJ BLB DSK FDN DFT TDM EOE TLA ECL TMT SOS MSH HOB'.split()
oi={s:i for i,s in enumerate(ORDER)}
df=o.copy(); df['type_line']=pool.type_line.values; df['si']=df.set.map(oi)
df['a']=df.actual_gih*100; df['p']=df.pred*100
smean_a=df.groupby('set').a.mean(); smean_p=df.groupby('set').p.mean()
byname={}
for n,s in zip(df.name,df.set): byname.setdefault(n,set()).add(s)
basic=df.type_line.fillna('').str.contains('Basic Land')
prior=[]
for n,s,bl in zip(df.name,df.set,basic):
    c=[x for x in byname[n] if oi[x]<oi[s]]
    prior.append(max(c,key=lambda x:oi[x]) if c and not bl else None)
df['prior_set']=prior; df['rep']=df.prior_set.notna()
pa={(r.set,r.name):0 for r in []}
pm=df.groupby(['set','name']).a.mean()
df['prior_delta']=[ (pm[(ps,n)]-smean_a[ps]) if isinstance(ps,str) else np.nan for ps,n in zip(df.prior_set,df.name)]
df['pred_delta']=df.p-df.set.map(smean_p)
df['d']=df.prior_delta-df.pred_delta; df['resid']=df.a-df.p
df['k']=np.nan; df['new_pred']=df.p
for S in ORDER:
    oth=df[df.rep&(df.set!=S)]; k=(oth.d*oth.resid).sum()/(oth.d**2).sum()
    m=df.rep&(df.set==S); df.loc[m,'k']=k; df.loc[m,'new_pred']=df.p[m]+k*df.d[m]
df['new_resid']=df.a-df.new_pred
df['ae0']=df.resid.abs(); df['ae1']=df.new_resid.abs()
rp=df[df.rep]
out={}
out['n_reprint']=int(len(rp)); out['per_set_n']=rp.groupby('set').size().reindex(ORDER).fillna(0).astype(int).to_dict()
out['by_rarity_ord']={str(k):int(v) for k,v in rp.groupby('rarity_ord').size().items()}
ks=rp.groupby('set').k.first(); out['k_range']=[float(ks.min()),float(ks.max())]; out['k_mean']=float(ks.mean()); out['k_per_set']=ks.to_dict()
out['reprint_mae_before']=float(rp.ae0.mean()); out['reprint_mae_after']=float(rp.ae1.mean())
df['ae1all']=df.ae1.where(df.rep,df.ae0)
ps0=df.groupby('set').ae0.mean(); ps1=df.groupby('set').ae1all.mean()
out['overall_mean_over_sets_before']=float(ps0.mean()); out['overall_mean_over_sets_after']=float(ps1.mean())
out['overall_pooled_before']=float(df.ae0.mean()); out['overall_pooled_after']=float(df.ae1all.mean())
g=rp.groupby('set')[['ae0','ae1']].mean(); cnt=rp.groupby('set').size(); g3=g[cnt>=3]
out['n_sets_ge3']=int(len(g3)); out['share_sets_improved']=float((g3.ae1<g3.ae0).mean()); out['n_sets_improved']=int((g3.ae1<g3.ae0).sum())
out['per_set_reprint_mae']={s:[float(r.ae0),float(r.ae1)] for s,r in g.iterrows()}
out['spearman_d_resid']=float(spearmanr(rp.d,rp.resid)[0])
c1=out['reprint_mae_before']-out['reprint_mae_after']>=0.10
c2=out['overall_mean_over_sets_after']<=out['overall_mean_over_sets_before'] and out['overall_pooled_after']<=out['overall_pooled_before']
c3=out['share_sets_improved']>=0.6
out['rule']={'c1_reprint_mae_drop_ge_0.10':bool(c1),'reprint_mae_drop':out['reprint_mae_before']-out['reprint_mae_after'],'c2_overall_not_worse':bool(c2),'c3_share_ge_0.6':bool(c3)}
out['verdict']='supported' if (c1 and c2 and c3) else 'not supported'
# recency split
df['gap']=df.si-df.prior_set.map(oi); rp=df[df.rep]
for nm,m in [('gap_1_4',rp.gap<=4),('gap_older',rp.gap>4)]:
    x=rp[m]; out['split_'+nm]={'n':int(len(x)),'before':float(x.ae0.mean()),'after':float(x.ae1.mean())}
# sanity
out['sanity']={'B11g_pooled_mae':float(df.ae0.mean()),'B11g_mean_over_sets':float(ps0.mean()),
 'B10_mean_over_sets':float((o10.actual_gih*100-o10.pred*100).abs().groupby(o10.set).mean().mean())}
# TRK
t=json.load(gzip.open('/home/claude/meatgoodbyeeee-wq/limited-forecast-pages/data/trk/target.json.gz','rt'))['cards']
nb=set(df[~basic].name); res=[]
for c in t:
    if c['name'] in nb: res.append((c['name'],c['rarity'],sorted(byname[c['name']],key=oi.get)))
out['trk_total']=len(t); out['trk_match']=len(res)
out['trk_match_by_rarity']=pd.Series([r[1] for r in res]).value_counts().to_dict()
out['trk_total_by_rarity']=pd.Series([c['rarity'] for c in t]).value_counts().to_dict()
out['trk_matches']=[{'name':n,'rarity':r,'sets':s} for n,r,s in res]
json.dump(out,open('result_q3.json','w'),indent=1,default=float)
rp[['set','name','rarity_ord','prior_set','prior_delta','pred_delta','d','resid','k','new_resid']].to_csv('q3_cards.csv.gz',index=False,compression='gzip')
print(json.dumps({k:v for k,v in out.items() if k not in('trk_matches','per_set_reprint_mae','k_per_set')},indent=1,default=float))
for r in res: print(r)
