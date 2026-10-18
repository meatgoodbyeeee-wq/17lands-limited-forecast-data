import sys, json
import numpy as np, pandas as pd

R = 'research/'
o = pd.read_csv(R + 'c9_power_questions/oof_B10.csv.gz')
f9 = pd.read_csv(R + 'c9_power_questions/c9_features.csv.gz')[['key', 'id', 'c9_m_GRADE']]
f5 = pd.read_csv(R + 'c5_atomic_effects/c5_features.csv.gz')
cards = pd.read_csv(R + 'c9_power_questions/cards.csv.gz')[['id', 'type_line', 'mv', 'colors']]

o['key'] = o['set'] + '|' + o['name']
n0 = len(o)
d = o.merge(f9, on='key', how='left').merge(f5.drop(columns=['id']), on='key', how='left').merge(cards, on='id', how='left')
miss = d['c9_m_GRADE'].isna().sum()
d = d.dropna(subset=['c9_m_GRADE'])
print('oof rows', n0, 'unjoined (no C9 feature)', miss, 'kept', len(d))

# set-centred, pp
d['a'] = (d.actual_gih - d.groupby('set').actual_gih.transform('mean')) * 100
d['p'] = (d.pred - d.groupby('set').pred.transform('mean')) * 100
d['g'] = d.c9_m_GRADE - d.groupby('set').c9_m_GRADE.transform('mean')
d['res'] = d.a - d.p

rm = d[d.rarity_ord >= 2].copy()
sl, ic = np.polyfit(rm.g, rm.a, 1)
rm['gap'] = rm.a - (ic + sl * rm.g)
print('R/M n', len(rm), 'slope pp per GRADE pt', round(sl, 3), 'icpt', round(ic, 3))
print('corr(g,a) R/M', round(np.corrcoef(rm.g, rm.a)[0, 1], 3), 'corr(gap,res)', round(np.corrcoef(rm.gap, rm.res)[0, 1], 3))

# groups
def main_type(t):
    if not isinstance(t, str): return 'Other'
    t = t.split('—')[0]
    for k in ['Planeswalker', 'Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment', 'Land']:
        if k in t: return k
    return 'Other'
rm['mtype'] = rm.type_line.map(main_type)
rm['mvbin'] = pd.cut(rm.mv.fillna(0), [-1, 2, 4, 6, 99], labels=['mv0-2', 'mv3-4', 'mv5-6', 'mv7+']).astype(str)
def ncol(c):
    if not isinstance(c, str) or c == '': return 'colourless'
    return 'mono' if len(c) == 1 else 'multi'
rm['ncol'] = rm.colors.map(ncol)
rm['rar'] = np.where(rm.rarity_ord == 3, 'M', 'R')

groups = {}
tags = [c for c in rm.columns if c.startswith('c5_')]
for t in tags:
    m = rm[t] > 0
    if m.sum() >= 15: groups[t] = m
for col, pre in [('mtype', 'type:'), ('mvbin', ''), ('ncol', 'col:'), ('rar', 'rar:')]:
    for v in rm[col].unique():
        m = rm[col] == v
        if m.sum() >= 15: groups[pre + v] = m

rows = []
for name, m in groups.items():
    s = rm[m]
    n = len(s)
    gm, rmn = s.gap.mean(), s.res.mean()
    gse, rse = s.gap.std() / np.sqrt(n), s.res.std() / np.sqrt(n)
    sign = np.sign(gm)
    per = s.groupby('set').filter(lambda x: len(x) >= 3).groupby('set').gap.mean()
    cons = int((np.sign(per) == sign).sum()); tot = len(per)
    rows.append(dict(group=name, n=n, gap_mean=gm, gap_t=gm / gse, res_mean=rmn, res_t=rmn / rse,
                     set_consistent=cons, sets=tot, consist=cons / tot if tot else np.nan,
                     systematic=bool(abs(gm / gse) >= 3 and tot and cons / tot >= 0.65)))
out = pd.DataFrame(rows).sort_values('gap_t')
out.to_csv('research/g1_grade_diagnosis/group_table.csv', index=False)
pd.set_option('display.width', 200); pd.set_option('display.max_rows', 200)
print('groups tested', len(out))
print(out.round(2).to_string(index=False))
print('systematic:', out[out.systematic].group.tolist())

# low GRADE but top-decile actual
thr = rm.groupby('set').a.transform(lambda x: x.quantile(0.9))
top = rm[rm.a >= thr]
low = top[top.c9_m_GRADE <= 3.0]
print('R/M top-10% actual:', len(top), ' of which GRADE<=3.0:', len(low), ' mean res of those', round(low.res.mean(), 2))
print(low.mtype.value_counts().to_dict(), low.rar.value_counts().to_dict())
print('top-decile mean GRADE', round(top.c9_m_GRADE.mean(), 2), 'mean g', round(top.g.mean(), 2), 'mean gap', round(top.gap.mean(), 2), 'mean res', round(top.res.mean(), 2))
aa = d[(d.set == 'MSH') & (d.name == 'Avengers Assemble!')].iloc[0]
s = d[d.set == 'MSH']
print('AA: GRADE', round(aa.c9_m_GRADE, 2), 'g', round(aa.g, 2), 'a', round(aa.a, 2), 'p', round(aa.p, 2),
      'rank actual', int((s.a > aa.a).sum() + 1), 'rank GRADE', int((s.c9_m_GRADE > aa.c9_m_GRADE).sum() + 1),
      'rank pred', int((s.p > aa.p).sum() + 1), 'of', len(s))
json.dump(dict(slope=sl, icpt=ic, n_rm=len(rm), groups=len(out), systematic=out[out.systematic].group.tolist()),
          open('research/g1_grade_diagnosis/result.json', 'w'), indent=1)
