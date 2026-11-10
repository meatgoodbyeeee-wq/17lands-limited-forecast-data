import pandas as pd, numpy as np, glob, json, sys
from scipy.stats import spearmanr, pearsonr
D=sys.argv[1]
rows=[]; allc=[]
for f in sorted(glob.glob(D+'/*_case6_28d.csv')):
    d=pd.read_csv(f); s=d['set'].iloc[0]
    m=json.load(open(f.replace('_28d.csv','_manifest.json')))
    if not m['has_user_wr_bucket']: rows.append(dict(set=s,top=False,start=m['window_start'][:10])); continue
    x=d[d.top60n50_games>=500].copy()
    x['top']=100*x.top60n50_wins/x.top60n50_games; x['ov']=100*x.all_wins/x.all_games
    x['nt']=100*(x.all_wins-x.top60n50_wins)/(x.all_games-x.top60n50_games)
    for h in ('h0','h1'):
        x['top_'+h]=100*x[f'top60n50_{h}_wins']/x[f'top60n50_{h}_games']
        x['ov_'+h]=100*x[f'all_{h}_wins']/x[f'all_{h}_games']
        x['nt_'+h]=100*(x[f'all_{h}_wins']-x[f'top60n50_{h}_wins'])/(x[f'all_{h}_games']-x[f'top60n50_{h}_games'])
    cols=['top','ov','nt','top_h0','top_h1','ov_h0','ov_h1','nt_h0','nt_h1']
    for c in cols: x[c+'_c']=x[c]-x[c].mean()
    b=np.polyfit(x.ov_c,x.top_c,1)[0]
    r=pearsonr(x.top_h0,x.top_h1)[0]; ro=pearsonr(x.ov_h0,x.ov_h1)[0]
    rows.append(dict(set=s,top=True,start=m['window_start'][:10],n=len(x),N=len(d),share=m['group_games']['top60n50']/m['group_games']['all'],
       gap=x.top.mean()-x.ov.mean(),sd_top=x.top.std(),sd_ov=x.ov.std(),sp=spearmanr(x.top,x.ov)[0],rel_top=2*r/(1+r),rel_ov=2*ro/(1+ro),b=b,
       resid_sd=(x.top_c-b*x.ov_c).std(), se_med=(100*np.sqrt(x.top/100*(1-x.top/100)/x.top60n50_games)).median()))
    allc.append(x)
R=pd.DataFrame(rows).sort_values('start'); pd.set_option('display.width',250); print(R.round(3).to_string(index=False))
T=R[R.top]; print('mean',T.drop(columns=['set','top','start']).mean().round(3).to_dict())
A=pd.concat(allc)
# d reliability
A['d']=A.top_c-A.ov_c; A['d2']=A.top_c-A.nt_c
def sb(r): return 2*r/(1+r)
r1=pearsonr(A.top_h0_c-A.ov_h0_c, A.top_h1_c-A.ov_h1_c)[0]
r2=pearsonr(A.top_h0_c-A.nt_h1_c, A.top_h1_c-A.nt_h0_c)[0]
print('d sd',A.d.std(),'d2 sd',A.d2.std(),'half corr d',r1,'SB',sb(r1),'| independent halves d2',r2,'SB',sb(r2))
# residual after slope: e = top_c - b*nt_c with pooled b ; split-half using independent halves
bp=np.polyfit(A.nt_c,A.top_c,1)[0]; print('pooled slope top on nontop',bp, 'top on overall',np.polyfit(A.ov_c,A.top_c,1)[0])
e0=A.top_h0_c-bp*A.nt_h1_c; e1=A.top_h1_c-bp*A.nt_h0_c; r3=pearsonr(e0,e1)[0]; print('resid (slope-adjusted) half corr',r3,'SB',sb(r3),'sd',(A.top_c-bp*A.nt_c).std())
big=A[A.top60n50_games>=2000]; r4=pearsonr(big.top_h0_c-bp*big.nt_h1_c,big.top_h1_c-bp*big.nt_h0_c)[0]; print('>=2000 games: n',len(big),'half corr',r4,'SB',sb(r4))
print('corr(d2, nt_c)',pearsonr(A.d2,A.nt_c)[0], 'N cards',len(A))
A.to_csv(sys.argv[2],index=False)
