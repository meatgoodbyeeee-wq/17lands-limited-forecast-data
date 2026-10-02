import csv
lab={}
for l in open('wk_one/labels.txt'):
    a=l.split()
    if a: lab['ONE'+a[0]]=a[1:]
rows=list(csv.DictReader(open('input/ONE.csv')))
codes=['WU','UB','BR','RG','GW','WB','UR','BG','RW','GU']
out=[];none=0;bad=0
for r in rows:
    p,s,ro=lab[r['id']]
    cols=set(r['colors'] or '')
    if p=='-': p='';none+=1
    if s=='-': s=''
    for c in ([p] if p else [])+(s.split('+') if s else []):
        assert c in codes,(r['id'],c)
        if not cols<=set(c): bad+=1;print('COLOUR',r['id'],r['name'],c)
    out.append([r['id'],p,s,ro])
assert len(out)==len(rows)==len(lab)
w=csv.writer(open('raw/ONE.csv','w',newline=''));w.writerow(['id','primary','secondary','role']);w.writerows(out)
print(len(out),none/len(out),bad)
