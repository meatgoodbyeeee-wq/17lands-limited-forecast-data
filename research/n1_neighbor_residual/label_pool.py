import sys,gzip,json,warnings
warnings.filterwarnings('ignore')
R='/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/17lands-limited-forecast-data/'
for p in ('c9_power_questions','gih_llm_extract','trk_preview'): sys.path.insert(0,R+'research/'+p)
sys.path.insert(0,R+'scripts')
import numpy as np,pandas as pd
import c9, c3_research as c3
pool,base,cols=c9.load_pool(); pool=pool.reset_index(drop=True)
print(pool.shape, pool.set.nunique())
lab=[c for c in pool.columns if c.startswith(('c4_','c5_')) and pool[c].dtype!=object]+[c for c in pool.columns if c.startswith('c9_m_')]+[c for c in cols if c in pool.columns]
lab=list(dict.fromkeys(lab)); print(len(lab))
L=json.load(gzip.open(R+'../limited-forecast-pages/data/similar-labels.json.gz','rt'))
print(lab==L['dims'])
mu=pool[lab].fillna(0).to_numpy(float).mean(0); sd=pool[lab].fillna(0).to_numpy(float).std(0)+1e-9
x=(pool[lab].fillna(0).to_numpy(float)-mu)/sd; x/=np.linalg.norm(x,axis=1,keepdims=True)+1e-9
V=np.rint(x*1000)
bad=0;n=0
for i,(s,nm) in enumerate(zip(pool.set,pool.name)):
    r=L['refs'].get(f'{s}|{nm}')
    if r is None: continue
    n+=1; 
    if np.abs(np.array(r)-V[i]).max()>2: bad+=1
print('checked',n,'mismatch',bad)
pool.to_pickle('/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/work/pool.pkl')
np.save('/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/work/labvec.npy',V)
json.dump(lab,open('/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/work/labdims.json','w'))
