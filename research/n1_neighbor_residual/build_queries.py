"""Build query objects for node (similar-card text vectors) for all 7,075 OOF cards. Reconstruct card objects from the feature tables."""
import json,gzip,re,sys
import numpy as np,pandas as pd
W='/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/'
pool=pd.read_pickle(W+'work/pool.pkl'); V=np.load(W+'work/labvec.npy')
refs=json.load(gzip.open(W+'limited-forecast-pages/data/similar-references.json.gz','rt'))['cards']
rk={(r['set'],r['name']):r for r in refs}
RAR=['common','uncommon','rare','mythic']
import collections
_t=collections.defaultdict(collections.Counter)
for (st,nm),c in rk.items():
    row=pool[(pool['set']==st)&(pool['name']==nm)]
    if len(row):
        rr=row.iloc[0]; _t[(int(rr.mana_symbols),float(rr.mv),int(rr.n_colors))][len(re.findall(r'\{[^}]*[WUBRG][^}]*\}',c['mana_cost'] or ''))]+=1
def recon(r):
    s=int(r.mana_symbols) if r.mana_symbols==r.mana_symbols else 0; m=float(r.mv)
    key=(s,m,int(r.n_colors)); pips=_t[key].most_common(1)[0][0] if key in _t else (s-1 if s<m else s)
    pips=max(pips,0)
    cols=[c for c in 'WUBRG' if r['color_'+c]>0]
    mc=('{1}' if s<m else '')+''.join('{%s}'%(cols[i%len(cols)] if cols else 'C') for i in range(pips))
    num=lambda x:'' if x!=x else str(int(x)) if float(x).is_integer() else str(x)
    return dict(id=r['name'],name=r['name'],set=r['set'],rarity=RAR[int(r.rarity_ord)],colors=cols,cmc=m,mana_cost=mc,type_line=r.type_line,oracle_text=r.oracle_text if r.oracle_text==r.oracle_text else '',power=num(r.power),toughness=num(r.toughness))
out=[];devrecon=0
for i,r in pool.iterrows():
    k=(r['set'],r['name'])
    q=dict(set=r['set'],name=r['name'],lv=V[i].astype(int).tolist(),recon=recon(r))
    if k in rk: q['site']={x:rk[k][x] for x in ('id','name','set','rarity','colors','cmc','mana_cost','type_line','oracle_text','power','toughness')}
    out.append(q)
# pips accuracy on dev
ok=[];
for q in out:
    if 'site' in q:
        f=lambda c:len(re.findall(r'\{[^}]*[WUBRG][^}]*\}',c['mana_cost'] or ''))
        ok.append(f(q['site'])==f(q['recon']))
print('queries',len(out),'dev with site obj',len(ok),'pips recon acc',np.mean(ok))
json.dump(out,open(W+'work/n1_queries.json','w'))
