import pandas as pd, numpy as np, sys
from scipy.stats import spearmanr
o=pd.read_csv(sys.argv[1]); g=pd.read_csv(sys.argv[2]).rename(columns={'pred':'b11g'})
seeds=['20260922','20260923','20260924']
for a in ['T0_overall_shift','T1_top_direct','T0+C3','T1+C3']:
    o[a]=o[[f'pred_{a}_s{s}' for s in seeds]].mean(axis=1)
o=o.merge(g[['set','name','b11g']],on=['set','name'],how='left')
arms=['T0_overall_shift','T1_top_direct','T0+C3','T1+C3','b11g']
o=o.dropna(subset=['b11g'])
for c in arms+['top_gih','actual_gih']: o[c+'_c']=100*(o[c]-o.groupby('set')[c].transform('mean'))
sets=sorted(o.set.unique()); print(len(sets),'sets',len(o),'cards')
res={}
for a in arms:
    m1=[];mk=[];sp=[];ks=[]
    for s in sets:
        tr=o[o.set!=s]; te=o[o.set==s]
        k=(tr[a+'_c']*tr.top_gih_c).sum()/(tr[a+'_c']**2).sum(); ks.append(k)
        m1.append((te[a+'_c']-te.top_gih_c).abs().mean()); mk.append((k*te[a+'_c']-te.top_gih_c).abs().mean()); sp.append(spearmanr(te[a+'_c'],te.top_gih_c)[0])
    res[a]=mk
    print(f'{a:18s} MAE k=1 {np.mean(m1):.3f}  MAE k(LOSO) {np.mean(mk):.3f}  k {np.mean(ks):.3f}  Spearman {np.mean(sp):.3f}')
# blend b11g*k and T1+C3*k
for pair in [('b11g','T0+C3'),('b11g','T1+C3'),('b11g','T1_top_direct'),('T0+C3','T1+C3')]:
    mk=[]
    for s in sets:
        tr=o[o.set!=s]; te=o[o.set==s]
        X=tr[[p+'_c' for p in pair]].to_numpy(); w=np.linalg.lstsq(X,tr.top_gih_c.to_numpy(),rcond=None)[0]
        mk.append((te[[p+'_c' for p in pair]].to_numpy()@w-te.top_gih_c).abs().mean())
    print('blend',pair,'MAE',round(np.mean(mk),3),'w',w.round(3), 'sets better than first alone', int((np.array(mk)<np.array(res[pair[0]])).sum()))
print('gap by set (top mean - overall mean, pp):'); gp=(100*(o.groupby('set').top_gih.mean()-o.groupby('set').actual_gih.mean())); print(gp.round(2).to_dict()); print('sd of gap',gp.std().round(3))
