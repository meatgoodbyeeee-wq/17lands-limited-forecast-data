import pandas as pd, numpy as np, glob, json, sys
from scipy.stats import spearmanr, pearsonr
D=sys.argv[1]; g=pd.read_csv(sys.argv[2]).rename(columns={'pred':'b11g','name':'card_name'})
fr=[]
for f in sorted(glob.glob(D+'/*_case6_28d.csv')):
    m=json.load(open(f.replace('_28d.csv','_manifest.json')))
    if not m['has_user_wr_bucket']: continue
    d=pd.read_csv(f); d['share64']=m['group_games']['top64n50']/m['group_games']['all']; d['share60']=m['group_games']['top60n50']/m['group_games']['all']
    d['gwr64']=m['group_game_win_rate']['top64n50']; fr.append(d)
A=pd.concat(fr).merge(g[['set','card_name','b11g','rarity_ord']],on=['set','card_name'],how='left')
def run(grp, sub=None, label=''):
    x=A[A[grp+'_games']>=500].copy() if sub is None else sub.copy()
    x['t']=100*x[grp+'_wins']/x[grp+'_games']; x['ov']=100*x.all_wins/x.all_games
    x['se2']=x.t*(100-x.t)/x[grp+'_games']
    for c in ['t','ov']: x[c+'_c']=x[c]-x.groupby('set')[c].transform('mean')
    out=[]
    for s,y in x.groupby('set'):
        b=np.polyfit(y.ov_c,y.t_c,1)[0]; res=y.t_c-b*y.ov_c
        out.append(dict(n=len(y),gap=y.t.mean()-y.ov.mean(),sd_t=y.t.std(),sd_ov=y.ov.std(),sp=spearmanr(y.t,y.ov)[0],pe=pearsonr(y.t,y.ov)[0],b=b,resid_sd=res.std(),
                        noise_sd=np.sqrt(y.se2.mean()),se_med=np.sqrt(y.se2).median(),rel_binom=1-y.se2.mean()/y.t.var(),true_resid_var=res.var()-y.se2.mean(),games_med=y[grp+'_games'].median()))
    o=pd.DataFrame(out); mm=o.mean()
    print(f'--- {grp} {label}: sets {len(o)}, cards {len(x)}, per set {mm.n:.0f} (min {o.n.min()})')
    print(f'  gap {mm.gap:.2f}  SD top {mm.sd_t:.2f} / overall {mm.sd_ov:.2f}  Spearman {mm.sp:.3f} (min {o.sp.min():.3f})  Pearson {mm.pe:.3f}  slope {mm.b:.3f}  resid SD {mm.resid_sd:.2f}')
    print(f'  binomial noise SD {mm.noise_sd:.2f} (median SE {mm.se_med:.2f}), reliability(binomial) {mm.rel_binom:.3f}, disattenuated Pearson {mm.pe/np.sqrt(max(mm.rel_binom,1e-9)):.3f}, true resid SD {np.sqrt(max(mm.true_resid_var,0)):.2f} (var {mm.true_resid_var:.2f}; sets with var>0: {(o.true_resid_var>0).sum()}), median games {mm.games_med:.0f}')
    # B11g
    z=x.dropna(subset=['b11g']).copy(); z['p_c']=100*(z.b11g-z.groupby('set').b11g.transform('mean'))
    for c in ['t','ov']: z[c+'_c']=z[c]-z.groupby('set')[c].transform('mean')
    mk=[];m1=[];sp=[];orc=[];spo=[]
    for s in z.set.unique():
        tr=z[z.set!=s]; te=z[z.set==s]
        k=(tr.p_c*tr.t_c).sum()/(tr.p_c**2).sum(); bo=(tr.ov_c*tr.t_c).sum()/(tr.ov_c**2).sum()
        mk.append((k*te.p_c-te.t_c).abs().mean()); m1.append((te.p_c-te.t_c).abs().mean()); sp.append(spearmanr(te.p_c,te.t_c)[0]); spo.append(spearmanr(te.p_c,te.ov_c)[0]); orc.append((bo*te.ov_c-te.t_c).abs().mean())
    print(f'  B11g: cards {len(z)}  k {k:.3f}  MAE k {np.mean(mk):.3f}  MAE k=1 {np.mean(m1):.3f}  Spearman vs top {np.mean(sp):.3f} / vs overall {np.mean(spo):.3f}  oracle MAE {np.mean(orc):.3f}')
    return x
print('game share top64n50 mean', A.groupby('set').share64.first().mean().round(4), ' top60n50', A.groupby('set').share60.first().mean().round(4), ' group win rate top64', A.groupby('set').gwr64.first().mean().round(4))
x64=run('top64n50'); run('top60n50'); run('top56n50')
run('top60n50', sub=A[A.top64n50_games>=500], label='(same cards as top64 >=500)')
# top64 vs top60 directly, and 60-64 band (top60n50 minus top64n50)
x=A[A.top64n50_games>=500].copy()
x['band_g']=x.top60n50_games-x.top64n50_games; x['band']=100*(x.top60n50_wins-x.top64n50_wins)/x.band_g
x['t64']=100*x.top64n50_wins/x.top64n50_games; x['nt']=100*(x.all_wins-x.top60n50_wins)/(x.all_games-x.top60n50_games)
for c in ['t64','band','nt']: x[c+'_c']=x[c]-x.groupby('set')[c].transform('mean')
r=x.groupby('set').apply(lambda y: pd.Series(dict(p64_band=pearsonr(y.t64,y.band)[0],p64_nt=pearsonr(y.t64,y.nt)[0],pband_nt=pearsonr(y.band,y.nt)[0],b64_nt=np.polyfit(y.nt_c,y.t64_c,1)[0],bband_nt=np.polyfit(y.nt_c,y.band_c,1)[0])))
print('independent groups (>=64 / 60-64 band / below 60), same cards:', r.mean().round(3).to_dict())
print('rarity mix top64 cards', x64.rarity_ord.value_counts(normalize=True).sort_index().round(3).to_dict(), ' all top60 cards', A[A.top60n50_games>=500].rarity_ord.value_counts(normalize=True).sort_index().round(3).to_dict())
