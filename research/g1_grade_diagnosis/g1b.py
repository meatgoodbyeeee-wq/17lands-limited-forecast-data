import numpy as np, pandas as pd
exec(open('research/g1_grade_diagnosis/g1.py').read().split("groups = {}")[0].replace("print(","(lambda *a,**k:None)("))
print('R/M n', len(rm))
# 1 calibration
print('slope a~p (R/M):', round(np.polyfit(rm.p, rm.a, 1)[0], 3), ' all rarities:', round(np.polyfit(d.p, d.a, 1)[0], 3))
for col in ['p', 'g']:
    rm['q'] = pd.qcut(rm[col].rank(method='first'), 10, labels=False) + 1
    t = rm.groupby('q').agg(n=('a', 'size'), a=('a', 'mean'), p=('p', 'mean'), res=('res', 'mean'), res_sd=('res', 'std'))
    t['res_t'] = t.res / (t.res_sd / np.sqrt(t.n))
    print('deciles by', col); print(t.drop(columns='res_sd').round(2).to_string())
# 2 nonlinear GRADE control
rm['gq'] = pd.qcut(rm.g.rank(method='first'), 10, labels=False)
rm['gap2'] = rm.a - rm.groupby('gq').a.transform('mean')
skip = {'c5_ntags', 'c5_ngroups', 'c5_nlvl2', 'c5_RATE', 'c5_CLK', 'c5_BLK'}
groups = {t: rm[t] > 0 for t in rm.columns if t.startswith('c5_') and t not in skip and (rm[t] > 0).sum() >= 15}
for col, pre in [('mtype', 'type:'), ('mvbin', ''), ('ncol', 'col:'), ('rar', 'rar:')]:
    for v in rm[col].unique():
        if (rm[col] == v).sum() >= 15: groups[pre + v] = rm[col] == v
first = pd.read_csv('research/g1_grade_diagnosis/group_table.csv').set_index('group')
rows = []
for name, m in groups.items():
    s = rm[m]; n = len(s)
    gm = s.gap2.mean(); gt = gm / (s.gap2.std() / np.sqrt(n)); rt = s.res.mean() / (s.res.std() / np.sqrt(n))
    per = s.groupby('set').filter(lambda x: len(x) >= 3).groupby('set').gap2.mean()
    cons, tot = int((np.sign(per) == np.sign(gm)).sum()), len(per)
    sys2 = bool(abs(gt) >= 3 and tot and cons / tot >= 0.65)
    rows.append(dict(group=name, n=n, gap2=gm, gap2_t=gt, res=s.res.mean(), res_t=rt, sets=f'{cons}/{tot}',
                     sys_first=bool(first.loc[name, 'systematic']) if name in first.index else None, sys_b=sys2))
out = pd.DataFrame(rows).sort_values('gap2_t'); out.to_csv('research/g1_grade_diagnosis/group_table_b.csv', index=False)
print('groups', len(out)); pd.set_option('display.width', 200)
print(out[(out.sys_b) | (out.sys_first == True)].round(2).to_string(index=False))
print('survivors:', out[out.sys_b & (out.sys_first == True)].group.tolist())
print('survivors with |res_t|>=3:', out[out.sys_b & (out.sys_first == True) & (out.res_t.abs() >= 3)].group.tolist())
print('AN:', out[out.group == 'c5_AN'].round(2).to_dict('records'))
