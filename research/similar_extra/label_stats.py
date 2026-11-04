#!/usr/bin/env python3
"""Distribution of the C3/C4/C5 label features: 28-set pool (Opus), TRK 336 cards (Sonnet), and the 707 extra cards (this run).
Standardised with the 28-set pool mean/std; C9 columns excluded (neutral for TRK and for the extras). Auto-labelled blank-text cards are excluded from the TRK/extra rows.
  python3 label_stats.py"""
import sys, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; R = HERE.parents[0]
for p in ('c9_power_questions', 'gih_llm_extract', 'trk_preview'):
    sys.path.insert(0, str(R / p))
import c9, c3_research as c3, trk_label as t, sonnet_check as sc  # noqa
pool, base, cols = c9.load_pool(); pool = pool.reset_index(drop=True)
lab = [c for c in pool.columns if c.startswith(('c4_', 'c5_')) and pool[c].dtype != object] + [c for c in pool.columns if c.startswith('c9_m_')] + [c for c in cols if c in pool.columns]
lab = list(dict.fromkeys(lab)); nc9 = [c for c in lab if not c.startswith('c9_m_')]
mu, sd = pool[lab].fillna(0).to_numpy(float).mean(0), pool[lab].fillna(0).to_numpy(float).std(0) + 1e-9
keep = [i for i, c in enumerate(lab) if not c.startswith('c9_m_')]

def stats(F, name):
    F = F.copy()
    for i, c in enumerate(lab):
        if c not in F.columns: F[c] = mu[i]
    Z = ((F[lab].fillna(0).to_numpy(float) - mu) / sd)[:, keep]
    n = np.linalg.norm(Z, axis=1)
    return dict(group=name, n=len(F), mean_abs_z=Z.__abs__().mean(), norm_mean=n.mean(), norm_sd=n.std(), norm_p10=np.percentile(n, 10), norm_p90=np.percentile(n, 90))

def table_for(csv, raws, rows):
    t3, t4, t5, _ = t.label_tables(rows, raws, with_c9=False)
    ft = t3.copy()
    for tab in (t4, t5):
        for c in tab.columns: ft[c] = tab[c].to_numpy(dtype=float)
    return ft

# extras
q = pd.read_csv(HERE / 'label/cards.csv', keep_default_na=False); q['mv'] = pd.to_numeric(q['mv'])
def load(p, d=HERE / 'label/raw', pat='c*_{}.txt'):
    out = {}
    for f in sorted(d.glob(pat.format(p))):
        for line in f.read_text().splitlines():
            if line.strip():
                r = sc.parse(p, line); out[r[0]] = r[1]
    return out
rx = {p: load(p) for p in ('c3', 'c4', 'c5')}
ex_rows = [r for r in q.itertuples() if r.auto == 0]
ft_x = table_for(None, rx, ex_rows)
# TRK (Sonnet)
qt = pd.read_csv(t.LAB / 'cards.csv.gz', keep_default_na=False)
raws_t = {p: d for p, (d, bad) in t.load_all().items()}
tr_rows = [r for r in qt.itertuples() if r.auto == 0 and all(r.id in raws_t[p] for p in t.LABEL_PASSES)]
ft_t = table_for(None, raws_t, tr_rows)
res = [stats(pool, 'pool 28 sets (Opus), all %d' % len(pool)), stats(ft_t, 'TRK (Sonnet), non-auto'), stats(ft_x, 'extra 707 (this run), non-auto')]
print(pd.DataFrame(res).round(3).to_string(index=False))

# raw label summaries
def c3stats(raw):
    a = pd.DataFrame([v[:10] for v in raw.values()], columns=c3.FIELDS)
    return a.mean()
pc3 = pd.DataFrame({'pool(Opus)': pool[[c for c in pool.columns if c in c3.FIELDS]].mean() if all(f in pool.columns for f in c3.FIELDS) else np.nan}) if False else None
cs = pd.DataFrame({'TRK(Sonnet)': c3stats(raws_t['c3']), 'extra': c3stats(rx['c3'])}).round(3)
print('\nC3 field means (raw digits):'); print(cs.T.to_string())
def role(raw):
    s = pd.Series([v[1] for v in raw.values()]); return (s.value_counts(normalize=True)).reindex(list('ADVFRTSNO')).fillna(0)
print('\nC4 role share:'); print(pd.DataFrame({'TRK(Sonnet)': role(raws_t['c4']), 'extra': role(rx['c4'])}).round(3).T.to_string())
nt = lambda raw: np.mean([len(v[1]) for v in raw.values()])
sc5 = lambda raw: pd.DataFrame([v[0] for v in raw.values()], columns=['RATE', 'CLK', 'BLK']).mean()
print('\nC5 tags per card: TRK %.2f extra %.2f' % (nt(raws_t['c5']), nt(rx['c5'])))
print(pd.DataFrame({'TRK(Sonnet)': sc5(raws_t['c5']), 'extra': sc5(rx['c5'])}).round(3).T.to_string())
# pool (Opus) C3 / C4 / C5 summaries from the pool columns when available
for nm, cs_ in (('c4_role', [c for c in pool.columns if c.startswith('c4_role_')]), ):
    print('\npool(Opus) C4 role share:', (pool[cs_].mean().rename(lambda x: x[-1])).round(3).to_dict())
c5t = [c for c in pool.columns if c.startswith('c5_') and c not in ('c5_ntags', 'c5_nlvl2', 'c5_ngroups') and c.split('_')[1] not in ('RATE', 'CLK', 'BLK')]
print('pool(Opus) c5_ntags mean %.2f ; TRK %.2f ; extra %.2f' % (pool['c5_ntags'].mean(), ft_t['c5_ntags'].mean(), ft_x['c5_ntags'].mean()))
for sc_ in ('c5_RATE', 'c5_CLK', 'c5_BLK'):
    if sc_ in pool.columns: print(sc_, 'pool %.2f TRK %.2f extra %.2f' % (pool[sc_].mean(), ft_t[sc_].mean(), ft_x[sc_].mean()))
