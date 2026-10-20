import sys, random, itertools, pandas as pd
import os
R=os.path.dirname(os.path.abspath(__file__))+'/../c9_power_questions/cards.csv.gz'
BASIC={'W':'Plains','U':'Island','B':'Swamp','R':'Mountain','G':'Forest'}
def pool(code):
    c=pd.read_csv(R); rows=[]
    for _,r in c.iterrows():
        for k in str(r['keys']).split(';'):
            if k.startswith(code+'|'):
                n=k.split('|',1)[1]
                if n in BASIC.values() or r['auto']==1 or '//' in n or 'Land' in str(r['type_line']): continue
                rows.append(dict(name=n,mv=r['mv'],colors=r['colors'] if isinstance(r['colors'],str) else '',tl=r['type_line']))
    return pd.DataFrame(rows).drop_duplicates('name')
def deck(p,pair,rng,force=None,drop=None):
    ok=p[p.colors.map(lambda c:set(c)<=set(pair))]
    spells=list(ok.name)
    if force and force in spells: spells.remove(force)
    chosen=rng.sample(spells,23-(1 if force else 0)); 
    if force: chosen.append(force)
    return chosen
def write(path,code,spells,pair):
    from collections import Counter
    ct=Counter(spells); lines=['[metadata]','Name='+path.split('/')[-1][:-4],'[Main]']
    lines+= [f'{n} {nm}|{code}' for nm,n in ct.items()]
    lines+= [f'8 {BASIC[pair[0]]}',f'9 {BASIC[pair[1]]}']
    open(path,'w').write('\n'.join(lines)+'\n')
