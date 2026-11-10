import pandas as pd, numpy as np, json, glob, os
from scipy.stats import spearmanr, pearsonr

B = '/home/claude/17lands-limited-forecast-data/research/case6/'
S = '/tmp/claude-0/-home-claude/9133dfa3-3ada-522e-bca4-5fd5c02090f8/scratchpad/'
OUT = S + 'top1/'
MING = 500
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 50); pd.set_option('display.max_rows', 500)

def sb(r): return 2 * r / (1 + r)
def pc(x, y): return pearsonr(x, y)[0]
def sc(x, y): return spearmanr(x, y)[0]

# ---------- load
man = {}; raw = {}
for f in sorted(glob.glob(B + 'data/*_case6_manifest.json')):
    m = json.load(open(f)); man[m['set']] = m
    raw[m['set']] = pd.read_csv(B + f"data/{m['set']}_case6_28d.csv")
order = sorted(man, key=lambda s: man[s]['window_start'])
nobucket = [s for s in order if not man[s]['has_user_wr_bucket']]
sets = [s for s in order if man[s]['has_user_wr_bucket']]
print('no bucket:', nobucket); print('with bucket:', len(sets), sets)

def prep(s, tag='top60n50'):
    d = raw[s].copy()
    d['all_g'] = d.all_games; d['all_w'] = d.all_wins
    d['t_g'] = d[f'{tag}_games']; d['t_w'] = d[f'{tag}_wins']
    d['n_g'] = d.all_g - d.t_g; d['n_w'] = d.all_w - d.t_w
    d = d[d.t_g >= MING].copy()
    d['top'] = d.t_w / d.t_g; d['ov'] = d.all_w / d.all_g; d['non'] = d.n_w / d.n_g
    if tag == 'top60n50':
        for h in ('h0', 'h1'):
            d[f'top_{h}'] = d[f'top60n50_{h}_wins'] / d[f'top60n50_{h}_games']
            d[f'all_{h}'] = d[f'all_{h}_wins'] / d[f'all_{h}_games']
            ng = d[f'all_{h}_games'] - d[f'top60n50_{h}_games']
            nw = d[f'all_{h}_wins'] - d[f'top60n50_{h}_wins']
            d[f'non_{h}'] = nw / ng
    return d

# ---------- A
rowsA = []; cards = {}
for s in sets:
    d = prep(s); cards[s] = d
    m = man[s]
    r = dict(set=s, window_start=m['window_start'][:10], n_target=len(d), n_all=len(raw[s]),
             top_share=m['group_games']['top60n50'] / m['group_games']['all'],
             top_gwr=m['group_game_win_rate']['top60n50'], all_gwr=m['group_game_win_rate']['all'])
    r['mean_diff_pp'] = (d.top.mean() - d.ov.mean()) * 100
    r['sd_top_pp'] = d.top.std(ddof=1) * 100; r['sd_ov_pp'] = d.ov.std(ddof=1) * 100
    r['sd_ratio'] = r['sd_top_pp'] / r['sd_ov_pp']
    r['spearman'] = sc(d.top, d.ov); r['pearson'] = pc(d.top, d.ov)
    r['rel_top'] = sb(pc(d.top_h0, d.top_h1)); r['rel_ov'] = sb(pc(d.all_h0, d.all_h1))
    r['rel_non'] = sb(pc(d.non_h0, d.non_h1))
    r['se_med_pp'] = np.median(np.sqrt(d.top * (1 - d.top) / d.t_g)) * 100
    tc = (d.top - d.top.mean()) * 100; oc = (d.ov - d.ov.mean()) * 100
    b, a = np.polyfit(oc, tc, 1)
    r['slope_b'] = b; r['resid_sd_pp'] = np.std(tc - (a + b * oc), ddof=2)
    rowsA.append(r)
A = pd.DataFrame(rowsA)
num = [c for c in A.columns if c not in ('set', 'window_start')]
mean_row = A[num].mean(); mean_row['set'] = 'MEAN(23)'; mean_row['window_start'] = ''
A2 = pd.concat([A, pd.DataFrame([mean_row])], ignore_index=True)
A.to_csv(OUT + 'A_by_set.csv', index=False)
A2.to_csv(OUT + 'A_by_set_with_mean.csv', index=False)

tj = json.load(open(B + 'top.json'))
tjd = pd.DataFrame(tj['descriptive']).set_index('set')
cmp = A.set_index('set')
chk = pd.DataFrame({
    'cards_mine': cmp.n_all, 'cards_tj': tjd.cards, 'tgt_mine': cmp.n_target, 'tgt_tj': tjd.cards_with_top_target,
    'diff_mine': cmp.mean_diff_pp, 'diff_tj': tjd.mean_top_minus_overall_pp,
    'sdT_mine': cmp.sd_top_pp, 'sdT_tj': tjd.sd_top_pp, 'sdO_mine': cmp.sd_ov_pp, 'sdO_tj': tjd.sd_overall_pp,
    'sp_mine': cmp.spearman, 'sp_tj': tjd.spearman_top_vs_overall, 'relT_mine': cmp.rel_top, 'relT_tj': tjd.reliability_top,
    'share_mine': cmp.top_share, 'share_tj': tjd.top_game_share, 'gwr_mine': cmp.top_gwr, 'gwr_tj': tjd.top_game_win_rate})
chk.to_csv(OUT + 'A_check_vs_top_json.csv')
print(chk.round(4).to_string())
# which sets are in the "new" group of top.json: find subset of size 7 whose tj means match descriptive_mean_new
import itertools
tjn = tj['descriptive_mean_new']['cards']
cand = [s for s in tjd.index if True]
best = None
for comb in itertools.combinations(tjd.index, 7):
    if abs(tjd.loc[list(comb), 'cards'].mean() - tjn) < 1e-9 and abs(tjd.loc[list(comb), 'spearman_top_vs_overall'].mean() - tj['descriptive_mean_new']['spearman_top_vs_overall']) < 1e-9:
        best = comb; break
print('new7 identified:', best)
new7 = list(best) if best else []
r16 = [s for s in tjd.index if s not in new7]
for nm, grp in (('research16', r16), ('new7', new7)):
    print(nm, grp)
    sub = A[A.set.isin(grp)]
    ref = tj['descriptive_mean_research16' if nm == 'research16' else 'descriptive_mean_new']
    mp = dict(cards='n_all', cards_with_top_target='n_target', top_game_share='top_share', top_game_win_rate='top_gwr', mean_top_minus_overall_pp='mean_diff_pp',
              spearman_top_vs_overall='spearman', reliability_top='rel_top', sd_top_pp='sd_top_pp', sd_overall_pp='sd_ov_pp', reliability_nontop='rel_non')
    out = pd.DataFrame({k: dict(mine=sub[v].mean(), tj=ref[k]) for k, v in mp.items()}).T
    out['diff'] = out.mine - out.tj
    print(out.round(4).to_string()); out.to_csv(OUT + f'A_check_group_{nm}.csv')

# ---------- B
P = []
for s in sets:
    d = cards[s].copy(); d['set'] = s
    cs = lambda c: (d[c] - d[c].mean()) * 100
    d['top_c'] = cs('top'); d['ov_c'] = cs('ov'); d['non_c'] = cs('non')
    d['d'] = d.top_c - d.ov_c; d['d2'] = d.top_c - d.non_c
    d['dh0'] = cs('top_h0') - cs('all_h0'); d['dh1'] = cs('top_h1') - cs('all_h1')
    d['d2a'] = cs('top_h0') - cs('non_h1'); d['d2b'] = cs('top_h1') - cs('non_h0')
    d['ovh0_c'] = cs('all_h0'); d['ovh1_c'] = cs('all_h1')
    f = d.t_g / d.all_g
    vt = d.top * (1 - d.top) / d.t_g; vn = d.non * (1 - d.non) / d.n_g
    d['se_d'] = (1 - f) * np.sqrt(vt + vn) * 100
    P.append(d)
P = pd.concat(P, ignore_index=True)
oo = pd.read_csv(S + 'in/oof_B11g.csv.gz')
P = P.merge(oo[['set', 'name', 'rarity_ord']].rename(columns={'name': 'card_name'}), on=['set', 'card_name'], how='left')
print('rarity missing:', P.rarity_ord.isna().sum(), 'of', len(P))
P['rarity'] = P.rarity_ord.map({0: 'C', 1: 'U', 2: 'R', 3: 'M'})
P[['set', 'card_name', 'rarity', 'ov_c', 'top_c', 'non_c', 'd', 'd2', 'se_d', 't_g']].to_csv(OUT + 'B_card_d.csv', index=False)

Bres = {}
Bres['n_cards'] = len(P)
Bres['d_mean'] = P.d.mean(); Bres['d_sd'] = P.d.std(ddof=1)
r = pc(P.dh0, P.dh1); Bres['d_split_r'] = r; Bres['d_split_SB'] = sb(r)
rs = [pc(g.dh0, g.dh1) for _, g in P.groupby('set')]
Bres['d_split_SB_setmean'] = np.mean([sb(x) for x in rs]); Bres['d_split_SB_set_min'] = min(sb(x) for x in rs); Bres['d_split_SB_set_max'] = max(sb(x) for x in rs)
Bres['d_split_SB_set_neg'] = sum(sb(x) < 0 for x in rs)
Bres['d_true_sd_implied'] = Bres['d_sd'] * np.sqrt(max(Bres['d_split_SB'], 0))
Bres['d_noise_sd_implied'] = Bres['d_sd'] * np.sqrt(1 - Bres['d_split_SB'])
Q = P.dropna(subset=['d2a', 'd2b'])
Bres['d2_n'] = len(Q); Bres['d2_sd'] = P.d2.std(ddof=1)
r2 = pc(Q.d2a, Q.d2b); Bres['d2_split_r'] = r2; Bres['d2_split_SB'] = sb(r2)
Bres['d2_true_sd_implied'] = Bres['d2_sd'] * np.sqrt(max(sb(r2), 0))
Bres['corr_d_ovc_pooled'] = pc(P.d, P.ov_c); Bres['spearman_d_ovc_pooled'] = sc(P.d, P.ov_c)
Bres['corr_d_ovc_setmean'] = np.mean([pc(g.d, g.ov_c) for _, g in P.groupby('set')])
Bres['slope_d_on_ovc'] = np.polyfit(P.ov_c, P.d, 1)[0]
Bres['corr_d2_ovc_pooled'] = pc(P.d2, P.ov_c)
# noise-robust: d from half 0 vs overall from half 1 (disjoint games), and vice versa
Bres['corr_dh0_ovh1'] = np.mean([pc(P.dh0, P.ovh1_c), pc(P.dh1, P.ovh0_c)])
Bres['slope_dh0_on_ovh1'] = np.mean([np.polyfit(P.ovh1_c, P.dh0, 1)[0], np.polyfit(P.ovh0_c, P.dh1, 1)[0]])
Bres['median_se_d'] = P.se_d.median(); Bres['rms_se_d'] = np.sqrt((P.se_d ** 2).mean())
rar = P.groupby('rarity').agg(n=('d', 'size'), d_mean=('d', 'mean'), d_sd=('d', 'std'), d_se=('d', lambda x: x.std() / np.sqrt(len(x))),
                              ov_c_mean=('ov_c', 'mean'), top_games_median=('t_g', 'median'), d2_mean=('d2', 'mean'))
rar = rar.reindex(['C', 'U', 'R', 'M']).reset_index()
rar.to_csv(OUT + 'B_rarity.csv', index=False)
P['ov_bin'] = pd.qcut(P.ov_c, 5, labels=False)
ovb = P.groupby('ov_bin').agg(n=('d', 'size'), ov_c_mean=('ov_c', 'mean'), d_mean=('d', 'mean'), d2_mean=('d2', 'mean')).reset_index()
ovb.to_csv(OUT + 'B_ovbins.csv', index=False)
lists = {}
for name, df in (('all500', P), ('ge2000', P[P.t_g >= 2000])):
    pos = df.sort_values('d', ascending=False).head(15); neg = df.sort_values('d').head(15)
    sm = df.assign(ad=df.d.abs()).sort_values('ad').head(15)
    lists[name] = (pos, neg, sm, len(df))
    for k, v in zip(('pos', 'neg', 'small'), (pos, neg, sm)):
        v[['set', 'card_name', 'rarity', 'ov_c', 'top_c', 'd', 'se_d', 't_g']].to_csv(OUT + f'B_list_{name}_{k}.csv', index=False)
G = P[P.t_g >= 2000]
Bres['n_ge2000'] = len(G); Bres['d_sd_ge2000'] = G.d.std(); Bres['rms_se_ge2000'] = np.sqrt((G.se_d ** 2).mean())
Bres['d_split_SB_ge2000'] = sb(pc(G.dh0, G.dh1))
Gq = G.dropna(subset=['d2a', 'd2b']); Bres['d2_split_SB_ge2000'] = sb(pc(Gq.d2a, Gq.d2b))
Bres['frac_abs_z_gt2'] = (P.d.abs() / P.se_d > 2).mean()
Bres['frac_abs_z_gt2_ge2000'] = (G.d.abs() / G.se_d > 2).mean()
perset = P.groupby('set').agg(d_sd=('d', 'std'), n=('d', 'size')).reindex(sets)
perset['d_split_SB'] = [sb(pc(P[P.set == s].dh0, P[P.set == s].dh1)) for s in sets]
def d2sb(s):
    q = P[P.set == s].dropna(subset=['d2a', 'd2b']); return sb(pc(q.d2a, q.d2b))
perset['d2_split_SB'] = [d2sb(s) for s in sets]
perset.to_csv(OUT + 'B_perset_d.csv')
json.dump({k: float(v) for k, v in Bres.items()}, open(OUT + 'B_summary.json', 'w'), indent=1)

# ---------- C
Cres = []
for model in ('B11g', 'B10'):
    o = pd.read_csv(S + f'in/oof_{model}.csv.gz')
    unm = []; parts = []
    for s in sets:
        d = cards[s]; oo_s = o[o.set == s]
        mm = d.merge(oo_s[['name', 'pred', 'actual_gih']], left_on='card_name', right_on='name', how='inner')
        unm.append(dict(set=s, model=model, target_cards=len(d), matched=len(mm), unmatched_target=len(d) - len(mm),
                        oof_rows=len(oo_s), oof_unmatched=len(oo_s) - len(mm),
                        max_abs_actual_vs_ov_pp=(mm.actual_gih - mm.ov).abs().max() * 100 if len(mm) else np.nan))
        mm['set'] = s
        mm['top_c'] = (mm.top - mm.top.mean()) * 100; mm['ov_c'] = (mm.ov - mm.ov.mean()) * 100
        mm['pred_c'] = (mm.pred - mm.pred.mean()) * 100
        parts.append(mm)
    U = pd.DataFrame(unm); U.to_csv(OUT + f'C_match_{model}.csv', index=False)
    M = pd.concat(parts, ignore_index=True)
    rows = []
    for s in sets:
        g = M[M.set == s]; tr = M[M.set != s]
        k = (tr.pred_c * tr.top_c).sum() / (tr.pred_c ** 2).sum()
        bo, ao = np.polyfit(tr.ov_c, tr.top_c, 1)
        rows.append(dict(model=model, set=s, n=len(g), sp_pred_top=sc(g.pred_c, g.top_c), sp_pred_ov=sc(g.pred_c, g.ov_c),
                         k=k, mae_top_k=(g.top_c - k * g.pred_c).abs().mean(), mae_top_k1=(g.top_c - g.pred_c).abs().mean(),
                         mae_ov_k1=(g.ov_c - g.pred_c).abs().mean(),
                         oracle_b=bo, oracle_a=ao, mae_oracle=(g.top_c - (ao + bo * g.ov_c)).abs().mean(),
                         mae_top_vs_ov_k1=(g.top_c - g.ov_c).abs().mean()))
    R = pd.DataFrame(rows); R.to_csv(OUT + f'C_by_set_{model}.csv', index=False)
    mean = R.drop(columns=['model', 'set']).mean(); mean['model'] = model
    Cres.append(mean)
    M.to_csv(OUT + f'C_matched_cards_{model}.csv', index=False)
    print(model, 'unmatched target', int(U.unmatched_target.sum()), 'oof unmatched', int(U.oof_unmatched.sum()), 'matched', int(U.matched.sum()))
C = pd.DataFrame(Cres); C.to_csv(OUT + 'C_summary.csv', index=False)

# ---------- D
rowsD = []
for tag in ('top56n50', 'top60n50', 'top64n50', 'top60'):
    per = []
    for s in sets:
        d = prep(s, tag)
        per.append(dict(set=s, n=len(d), diff=(d.top.mean() - d.ov.mean()) * 100 if len(d) else np.nan,
                        sd_top=d.top.std() * 100 if len(d) > 2 else np.nan, sd_ov=d.ov.std() * 100 if len(d) > 2 else np.nan,
                        sp=sc(d.top, d.ov) if len(d) > 5 else np.nan))
    pp = pd.DataFrame(per); pp.to_csv(OUT + f'D_{tag}_by_set.csv', index=False)
    rowsD.append(dict(tag=tag, n_cards_mean=pp.n.mean(), n_cards_total=pp.n.sum(), min_n=pp.n.min(), diff_pp=pp['diff'].mean(), sd_top_pp=pp.sd_top.mean(),
                      sd_ov_pp=pp.sd_ov.mean(), sd_ratio=(pp.sd_top / pp.sd_ov).mean(), spearman=pp.sp.mean()))
D = pd.DataFrame(rowsD); D.to_csv(OUT + 'D_summary.csv', index=False)

# ---------- print
print('\nA'); print(A2.round(3).to_string())
print('\nB'); print(json.dumps({k: round(float(v), 4) for k, v in Bres.items()}, indent=1))
print(rar.round(3).to_string()); print(ovb.round(3).to_string()); print(perset.round(3).to_string())
for name, (pos, neg, sm, n) in lists.items():
    print('\nLIST', name, n)
    for k, v in (('pos', pos), ('neg', neg)):
        print(k); print(v[['set', 'card_name', 'rarity', 'ov_c', 'top_c', 'd', 'se_d', 't_g']].round(2).to_string(index=False))
print('\nC'); print(C.round(3).to_string())
print('\nD'); print(D.round(3).to_string())
