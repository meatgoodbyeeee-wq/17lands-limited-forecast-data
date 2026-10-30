import glob,re,sys,csv,subprocess,unicodedata,shutil,os,json,time
W=os.getcwd(); G=W+'/forge'; B=W+'/forgefull'; REF='7b9f05426ee11f4b9b78a7ca017cc6416abdbc54'
CF=G+'/forge-gui/res/cardsfolder'
def git(*a): return subprocess.run(['git','-C',G,*a],capture_output=True,text=True)
def norm(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
rows=list(csv.DictReader(open('cards_needed.csv')))
need=sorted({r['set'] for r in rows})
dates={}
for f in glob.glob(G+'/forge-gui/res/editions/*.txt'):
    code=date=None
    for l in open(f,encoding='utf-8',errors='replace'):
        l=l.strip()
        if l.startswith('[') and l!='[metadata]': break
        if l.startswith('Code='): code=l[5:]
        if l.startswith('Date='): date=l[5:]
    if code in need: dates[code]=date
pats={'all':[r'AI:RemoveDeck:All',r'SVar:RemAIDeck:True'],'rand':[r'AI:RemoveDeck:Random',r'SVar:RemRandomDeck:True']}
forms={}
def scan(c):
    F='forge-gui/res/cardsfolder'
    ls=subprocess.run(['git','-C',B,'ls-tree','-r',c,F],capture_output=True,text=True).stdout.splitlines()
    shas=[];
    for l in ls:
        meta,path=l.split('\t',1)
        if path.endswith('.txt'): shas.append(meta.split()[2])
    p=subprocess.run(['git','-C',B,'cat-file','--batch'],input=('\n'.join(shas)+'\n').encode(),capture_output=True).stdout
    d={};i=0
    while i<len(p):
        j=p.index(b'\n',i); h=p[i:j].split(); n=int(h[2]); t=p[j+1:j+1+n].decode('utf-8','replace'); i=j+1+n+1
        m=re.search(r'^Name:(.*)$',t,re.M)
        if not m: continue
        a=[int(any(re.search(x,t) for x in pats[k])) for k in('all','rand')]
        for m2 in re.finditer(r'(AI:RemoveDeck:\w+|SVar:RemAIDeck:\w+|SVar:RemRandomDeck:\w+|RemoveDeck\w*)',t): forms[m2.group(1)]=forms.get(m2.group(1),0)+1
        k=norm(m.group(1).strip())
        if k in d: a=[max(a[0],d[k][0]),max(a[1],d[k][1])]
        d[k]=a
    return d
t0=time.time()
commits={}
for s in need: commits[s]=subprocess.run(['git','-C',B,'rev-list','-1',f'--before={dates[s]} 23:59:59 +0000',REF],capture_output=True,text=True).stdout.strip() #,'-1',f'--before={dates[s]} 23:59:59 +0000',REF).stdout.strip()
print(dates,commits,flush=True)
res={}
for s in sorted(need,key=lambda s:dates[s]):
    forms.clear(); res[s]=scan(commits[s]); print(s,dates[s],commits[s][:10],len(res[s]),dict(forms),round(time.time()-t0),flush=True)
forms.clear(); today=scan(REF); print('TODAY',len(today),dict(forms),round(time.time()-t0))
out=csv.writer(open('marks.csv','w',newline=''))
out.writerow('set,name,release_date,release_commit,found_release,mark_all_release,mark_random_release,found_today,mark_all_today,mark_random_today'.split(','))
um=[]
for r in rows:
    n=norm(r['name'].split(' // ')[0]); a=res[r['set']].get(n); b=today.get(n)
    if a is None or b is None: um.append((r['set'],r['name'],a is not None,b is not None))
    out.writerow([r['set'],r['name'],dates[r['set']],commits[r['set']],int(a is not None),a[0] if a else '',a[1] if a else '',int(b is not None),b[0] if b else '',b[1] if b else ''])
json.dump(um,open('unmatched.json','w'))
