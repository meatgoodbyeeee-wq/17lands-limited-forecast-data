import pandas as pd, numpy as np, json
C='/home/claude/17lands-limited-forecast-data/research/c9_power_questions/'
u=pd.read_csv(C+'cards.csv.gz',keep_default_na=False)
k2={}
for r in u.itertuples():
    for k in r.keys.split(';'): k2[k]=r
o=pd.read_csv(C+'oof_B10.csv.gz')
o['delta']=(o.actual_gih-o.groupby('set').actual_gih.transform('mean'))*100
o['pdelta']=(o.pred-o.groupby('set').pred.transform('mean'))*100
o['key']=o.set+'|'+o.name
assert o.key.isin(k2).all()
RM={2:'R',3:'M'}
def fmt(r,tag):
    c=k2[r.key]; pt=f' | {c.pt}' if c.pt else ''
    return f"{tag} | {RM[r.rarity_ord]} | MV {c.mv} {c.colors or 'C'} | {c.type_line}{pt}\n{c.btext}"
rm=o[o.rarity_ord>=2]
ex=rm[rm.set!='MSH'].groupby('set',group_keys=False).apply(lambda g:g.sample(min(len(g),30),random_state=1)).sample(frac=1,random_state=2)
tg=rm[rm.set=='MSH'].sample(frac=1,random_state=3).reset_index(drop=True)
lines=[]
for i,r in enumerate(ex.itertuples()):
    lines.append(fmt(r,f'#E{i+1}')+f"\n=> {r.delta:+.1f}\n")
open('examples.txt','w').write('\n'.join(lines))
tl=[fmt(r,f'#T{i+1}') for i,r in enumerate(tg.itertuples())]
open('targets.txt','w').write('\n\n'.join(tl)+'\n')
tg[['key','rarity_ord','delta','pdelta']].assign(tid=[f'T{i+1}' for i in range(len(tg))]).to_csv('targets_key.csv',index=False)
print(len(ex),len(tg), sum(len(l) for l in lines)/4)
