import csv
S='wk_one/'
lab={}
for f in 'l1 l2 l3'.split():
    for l in open(S+f+'.txt'):
        i,p,s,r=l.split(); lab['TDM'+i]=(p,s,r)
rows=list(csv.DictReader(open('input/TDM.csv')))
assert set(lab)=={r['id'] for r in rows} and len(rows)==len(lab)
bad=0;none=0
with open('raw/TDM.csv','w',newline='') as f:
    w=csv.writer(f);w.writerow(['id','primary','secondary','role'])
    for r in rows:
        p,s,ro=lab[r['id']]
        codes=[] if p=='-' else [p]+([] if s=='-' else s.split('+'))
        for c in codes:
            if not set(r['colors'])<=set(c): bad+=1;print('bad',r['id'],r['colors'],c)
        if p=='-': none+=1
        w.writerow([r['id'],'none' if p=='-' else p,'' if s=='-' else s,ro])
print(len(rows),none/len(rows),bad)
