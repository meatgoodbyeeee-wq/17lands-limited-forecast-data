"""N1: neighbour lists for V3 (tag/type/rarity weighted) and C0 (random). Outcome-free (labels, class, mv, rarity only)."""
import json,gzip,pickle
import numpy as np,pandas as pd
W='/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/'
pool=pd.read_pickle(W+'work/pool.pkl').reset_index(drop=True); V=np.load(W+'work/labvec.npy')/1000.0
dims=json.load(open(W+'work/labdims.json'))
refs=pd.DataFrame(json.load(gzip.open(W+'limited-forecast-pages/data/similar-references.json.gz','rt'))['cards'])
oof=pd.read_csv(W+'17lands-limited-forecast-data/research/c9_power_questions/oof_B10.csv.gz')
pool['key']=pool.set+'|'+pool.name
assert pool.key.is_unique, pool.key[pool.key.duplicated()].head()
cls=lambda t:0 if 'Land' in (t or '') and True and __import__('re').search(r'\bLand\b',t or '') else (1 if __import__('re').search(r'\bCreature\b',t or '') else 2)
pool['cls']=pool.type_line.map(cls)
oofsets=set(oof.set)
cm=refs[refs.set.isin(oofsets)&(refs.gih_n>=3000)]
ck=set((cm.set+'|'+cm.name))
cidx=np.array([i for i,k in enumerate(pool.key) if k in ck])
print('candidates',len(cidx))
tagd=[i for i,d in enumerate(dims) if d.startswith('c5_') and len(d)==5]
print('tag dims',len(tagd))
def nrm(X): return X/(np.linalg.norm(X,axis=1,keepdims=True)+1e-9)
Vl=nrm(V); Vt=nrm(V[:,tagd]); Vt[np.linalg.norm(V[:,tagd],axis=1)<1e-9]=0
mv=pool.mv.to_numpy(float); rar=pool.rarity_ord.to_numpy(); cl=pool.cls.to_numpy(); st=pool.set.to_numpy(); keys=pool.key.to_numpy()
rng=np.random.default_rng(20261023)
out={}
for i in range(len(pool)):
    c=cidx[st[cidx]!=st[i]]
    s=Vt[c]@Vt[i]+0.5*(Vl[c]@Vl[i])+0.25*(rar[c]==rar[i])
    ok=(cl[c]==cl[i])&(np.abs(mv[c]-mv[i])<=2)
    o=np.argsort(-s)
    okl=[j for j in o if ok[j]][:60]; nol=[j for j in o if not ok[j]][:20]
    ci=np.flatnonzero(ok); pr=rng.permutation(ci)[:60]
    out[keys[i]]={'v3':[[keys[c[j]],float(s[j])] for j in okl],'v3no':[[keys[c[j]],float(s[j])] for j in nol],
                  'c0':[[keys[c[j]],1.0] for j in pr],'c0no':[[keys[c[j]],1.0] for j in rng.permutation(np.flatnonzero(~ok))[:20]]}
json.dump(out,open(W+'work/n1_lists_py.json','w'))
print('done')
