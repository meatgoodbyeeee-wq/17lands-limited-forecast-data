import csv,glob
lab={}
for f in sorted(glob.glob('/tmp/claude-0/l/p*.txt')):
    for l in open(f):
        i,p,s,r=l.rstrip('\n').split('|'); lab['MKM'+i]=(p,s,r)
rows=list(csv.DictReader(open('input/MKM.csv')))
w=csv.writer(open('raw/MKM.csv','w',newline=''))
w.writerow(['id','primary','secondary','role'])
bad=0;none=0
for r in rows:
    p,s,rl=lab[r['id']]
    cols=set(r['colors'])
    for c in [p]+s.split('+'):
        if c not in('none','') and cols and not cols<=set(c): print('COLOUR',r['id'],c);bad+=1
    none+=p=='none'
    w.writerow([r['id'],p,s,rl])
print(len(rows),len(lab),none/len(rows),bad)
