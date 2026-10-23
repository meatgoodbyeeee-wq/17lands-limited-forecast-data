"""D1: diagnosis of systematic errors in C9 GRADE (see PLAN.md).  python3 d1.py   (run from anywhere)"""
import itertools, json, re
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parents[0]
SEED, NB, Q = 20261023, 2000, 0.1
C9 = R / 'c9_power_questions'


def load():
    o = pd.read_csv(C9 / 'oof_B10.csv.gz'); o['key'] = o['set'] + '|' + o['name']
    c = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    c['key'] = c['keys'].str.split(';'); c = c.explode('key').drop(columns=['keys', 'id'])
    f = pd.read_csv(C9 / 'c9_features.csv.gz')[['key', 'c9_m_GRADE', 'c9_s_GRADE']]
    t = pd.read_csv(R / 'c5_atomic_effects/c5_features.csv.gz')
    tags = [x for x in t.columns if x.startswith('c5_') and x[3:].isupper() and len(x) == 5 and x[3:] not in ('RATE',)]
    tags = [x for x in tags if x not in ('c5_CLK', 'c5_BLK')]
    d = o.merge(c, on='key', how='left').merge(f, on='key', how='left').merge(t[['key'] + tags], on='key', how='left')
    assert d['auto'].notna().all() and d['c9_m_GRADE'].notna().all()
    d = d[d['auto'] == 0].copy()
    d[tags] = d[tags].fillna(0)
    return d, [x[3:] for x in tags]


def prep(d):
    d['act_rel'] = (d['actual_gih'] - d.groupby('set')['actual_gih'].transform('mean')) * 100
    d['pred_rel'] = (d['pred'] - d.groupby('set')['pred'].transform('mean')) * 100
    d['resid'] = d['act_rel'] - d['pred_rel']
    d['rm'] = d['rarity_ord'] >= 2
    d['gap'] = np.nan
    fits = []
    for name, m in (('RM', d['rm']), ('CU', ~d['rm'])):
        for s in sorted(d['set'].unique()):
            tr = d[m & (d['set'] != s)]; te = m & (d['set'] == s)
            b, a = np.polyfit(tr['c9_m_GRADE'], tr['act_rel'], 1)
            d.loc[te, 'gap'] = d.loc[te, 'act_rel'] - (a + b * d.loc[te, 'c9_m_GRADE'])
            fits.append({'stratum': name, 'held_out': s, 'slope_pp_per_grade': b, 'intercept': a})
    fits = pd.DataFrame(fits)
    return d, fits


def features(d, tags):
    txt = d['btext'].str.lower()
    G = {}
    for t in tags: G[f'tag:{t}'] = d[f'c5_{t}'] > 0
    ty = d['type_line']
    for k in ['Creature', 'Instant', 'Sorcery', 'Enchantment', 'Artifact', 'Planeswalker', 'Land']:
        G[f'type:{k}'] = ty.str.contains(k)
    tokre = re.compile(r'create[^.\n]*token')
    G['text:token_creation'] = txt.apply(lambda s: bool(tokre.search(s)))
    big = re.compile(r'create[^.\n]*?(\d+)/(\d+)[^.\n]*?token')
    G['text:large_token(P>=4)'] = txt.apply(lambda s: any(int(m.group(1)) >= 4 for m in big.finditer(s)))
    G['hyp:AN&FH'] = (d['c5_AN'] > 0) & (d['c5_FH'] > 0)
    G['hyp:AN&DR'] = (d['c5_AN'] > 0) & (d['c5_DR'] > 0)
    G['hyp:AN&FH&DR'] = G['hyp:AN&FH'] & (d['c5_DR'] > 0)
    G['hyp:AN&CD'] = (d['c5_AN'] > 0) & (d['c5_CD'] > 0)
    G['hyp:TK&FL'] = (d['c5_TK'] > 0) & (d['c5_FL'] > 0)
    G['rarity:R'] = d['rarity_ord'] == 2; G['rarity:M'] = d['rarity_ord'] == 3
    G['rarity:C'] = d['rarity_ord'] == 0; G['rarity:U'] = d['rarity_ord'] == 1
    nl = ~ty.str.contains('Land')
    mv = d['mv']
    for lab, m in (('0-1', mv <= 1), ('2', mv == 2), ('3', mv == 3), ('4', mv == 4), ('5', mv == 5), ('6+', mv >= 6)):
        G[f'mv:{lab}'] = m & nl
    nc = d['colors'].str.len()
    for lab, m in (('0', nc == 0), ('1', nc == 1), ('2', nc == 2), ('3+', nc >= 3)): G[f'ncolor:{lab}'] = m
    kws = {'flying': r'\bflying\b', 'flash': r'\bflash\b', 'haste': r'\bhaste\b', 'trample': r'\btrample\b', 'deathtouch': r'\bdeathtouch\b',
           'lifelink': r'\blifelink\b', 'vigilance': r'\bvigilance\b', 'first_strike': r'\b(?:first|double) strike\b', 'menace': r'\bmenace\b',
           'reach': r'\breach\b', 'ward': r'\bward\b', 'hexproof': r'\bhexproof\b', 'indestructible': r'\bindestructible\b', 'defender': r'\bdefender\b'}
    for k, p in kws.items(): G[f'kw:{k}'] = txt.str.contains(p, regex=True)
    G['cd:CD>0'] = d['c5_CD'] > 0; G['cd:CD=0'] = d['c5_CD'] == 0
    return {k: v.to_numpy(bool) for k, v in G.items()}


def pair_groups(d, tags, top=30):
    X = {t: (d[f'c5_{t}'] > 0).to_numpy() for t in tags}
    cnt = sorted(((int((X[a] & X[b]).sum()), a, b) for a, b in itertools.combinations(tags, 2)), reverse=True)[:top]
    return {f'pair:{a}&{b}': X[a] & X[b] for _, a, b in cnt}


def bh(p, q=Q):
    p = np.asarray(p); n = len(p); o = np.argsort(p); r = np.empty(n, bool)
    th = p[o] <= q * (np.arange(1, n + 1) / n)
    k = np.max(np.where(th)[0]) + 1 if th.any() else 0
    r[o[:k]] = True
    return r


def eb(m, se):
    m, se = np.asarray(m, float), np.asarray(se, float)
    w = 1 / se ** 2; mu = (w * m).sum() / w.sum()
    Qs = (w * (m - mu) ** 2).sum(); c = w.sum() - (w ** 2).sum() / w.sum()
    tau2 = max(0.0, (Qs - (len(m) - 1)) / c)
    return mu + tau2 / (tau2 + se ** 2) * (m - mu), tau2, mu


def table(d, G, minn, nmin_test, center=None):
    sets = sorted(d['set'].unique()); si = d['set'].map({s: i for i, s in enumerate(sets)}).to_numpy()
    rng = np.random.default_rng(SEED)
    W = np.stack([np.bincount(rng.integers(0, len(sets), len(sets)), minlength=len(sets)) for _ in range(NB)]).astype(float)  # NB x S
    rows = []
    for g, mask in G.items():
        n = int(mask.sum())
        if n < minn: continue
        r = {'group': g, 'n': n}
        cnt = np.bincount(si[mask], minlength=len(sets)).astype(float)
        for v in ('gap', 'resid'):
            x = d[v].to_numpy(); c0 = 0.0 if center is None else center[v]
            sm = np.bincount(si[mask], weights=x[mask], minlength=len(sets))
            den = W @ cnt; ok = den > 0
            b = (W @ sm)[ok] / den[ok] - c0
            m = x[mask].mean() - c0
            r[f'{v}_mean'] = m; r[f'{v}_raw_mean'] = x[mask].mean(); r[f'{v}_lo'], r[f'{v}_hi'] = np.percentile(b, [2.5, 97.5]); r[f'{v}_se'] = b.std(ddof=1)
            r[f'{v}_p'] = min(1.0, 2 * (min((b <= 0).sum(), (b >= 0).sum()) + 1) / (len(b) + 1))
            ps = cnt >= 2
            sg = np.sign(sm[ps] / cnt[ps] - c0)
            r[f'{v}_same_sign_sets'] = float((sg == np.sign(m)).mean()) if ps.any() else np.nan
        r['n_sets'] = int((cnt >= 2).sum()); r['act_rel_mean'] = d['act_rel'].to_numpy()[mask].mean()
        r['grade_mean'] = d['c9_m_GRADE'].to_numpy()[mask].mean(); r['grade_sd_passes'] = d['c9_s_GRADE'].to_numpy()[mask].mean()
        rows.append(r)
    t = pd.DataFrame(rows)
    t['ref'] = t['n'] < nmin_test
    big = ~t['ref'].to_numpy()
    for v in ('gap', 'resid'):
        t[f'{v}_bh'] = False; t[f'{v}_shrunk'] = np.nan
        if big.sum() > 2:
            t.loc[big, f'{v}_bh'] = bh(t.loc[big, f'{v}_p'].to_numpy())
            sh, tau2, mu = eb(t.loc[big, f'{v}_mean'], t.loc[big, f'{v}_se'])
            t.loc[big, f'{v}_shrunk'] = sh; t.attrs[f'{v}_tau2'] = tau2
    return t


def classify(t):
    def f(r):
        if r['ref']: return 'ref'
        gs, rs = r['gap_bh'], r['resid_bh']
        same = np.sign(r['gap_mean']) == np.sign(r['resid_mean'])
        if rs: return 'A1_resid_GRADE_linked' if (gs and same) else 'A2_resid_not_GRADE'
        if gs: return 'B_gap_corrected'
        return 'none'
    t['class'] = t.apply(f, axis=1)
    return t


def run_stratum(d, tags, name, m):
    s = d[m].reset_index(drop=True)
    G = features(s, tags); G.update(pair_groups(s, tags))
    G = {k: v for k, v in G.items() if not (name == 'RM' and k in ('rarity:C', 'rarity:U')) and not (name == 'CU' and k in ('rarity:R', 'rarity:M'))}
    minn = 10
    t = classify(table(s, G, minn, 30))
    t.to_csv(HERE / f'groups_{name}.csv', index=False, float_format='%.4f')
    return s, G, t


def main():
    d, tags = load(); d, fits = prep(d)
    fits.groupby('stratum')[['slope_pp_per_grade', 'intercept']].agg(['mean', 'min', 'max']).round(3).to_csv(HERE / 'fit_summary.csv')
    out = {}
    res = {}
    for name, m in (('RM', d['rm']), ('CU', ~d['rm'])):
        s, G, t = run_stratum(d, tags, name, m)
        res[name] = (s, G, t)
        out[name] = {'n_cards': len(s), 'mean_gap': s['gap'].mean(), 'mean_resid': s['resid'].mean(), 'mean_act_rel': s['act_rel'].mean(),
                     'corr_grade_actrel': float(np.corrcoef(s['c9_m_GRADE'], s['act_rel'])[0, 1]), 'tau2_gap': t.attrs.get('gap_tau2'), 'tau2_resid': t.attrs.get('resid_tau2'),
                     'class_counts': t['class'].value_counts().to_dict(),
                     'exploratory_slope_resid_on_gap': float(np.polyfit(s['gap'], s['resid'], 1)[0])}
    # top 10 by actual GIH per set (all rarities); gap uses each card's own stratum fit
    d['top10'] = d.groupby('set')['actual_gih'].rank(ascending=False, method='first') <= 10
    s = d[d['top10']].reset_index(drop=True)
    G = features(s, tags); G.update(pair_groups(s, tags, 20))
    ctr = {'gap': s['gap'].mean(), 'resid': s['resid'].mean()}
    t = classify(table(s, G, 10, 10, center=ctr))
    t.to_csv(HERE / 'groups_top10.csv', index=False, float_format='%.4f')
    out['top10'] = {'n_cards': len(s), 'mean_gap': ctr['gap'], 'mean_resid': ctr['resid'], 'mean_act_rel': s['act_rel'].mean(),
                    'rarity_counts': s['rarity_ord'].value_counts().sort_index().to_dict(), 'class_counts': t['class'].value_counts().to_dict()}
    # exploratory (not pre-registered): top-10 cards by GRADE band
    s['gband'] = pd.cut(s['c9_m_GRADE'], [-1, 4, 5.5, 7, 11], labels=['<=4', '4-5.5', '5.5-7', '>7'])
    ex = s.groupby('gband', observed=True).agg(n=('gap', 'size'), gap=('gap', 'mean'), resid=('resid', 'mean'), act_rel=('act_rel', 'mean'))
    ex.to_csv(HERE / 'top10_by_grade_band.csv', float_format='%.3f')
    out['top10']['by_grade_band'] = ex.round(3).to_dict('index')
    # named cards
    rows = []
    sRM, GRM, tRM = res['RM']
    d['rank_act'] = d.groupby('set')['actual_gih'].rank(ascending=False, method='first')
    d['rank_b10'] = d.groupby('set')['pred'].rank(ascending=False, method='first')
    for key in ('MSH|Avengers Assemble!', 'ECL|Chronicle of Victory'):
        r = d[d['key'] == key].iloc[0]
        i = sRM.index[sRM['key'] == key][0]
        row = {'key': key, 'grade_mean': r['c9_m_GRADE'], 'grade_sd': r['c9_s_GRADE'], 'gap': r['gap'], 'resid': r['resid'], 'act_rel': r['act_rel'],
               'rank_actual': int(r['rank_act']), 'rank_b10': int(r['rank_b10']), 'tags': ','.join(t for t in tags if r[f'c5_{t}'] > 0)}
        mem = [(g, tRM.set_index('group').loc[g]) for g in GRM if GRM[g][i] and g in set(tRM['group'])]
        row['groups'] = ' | '.join(f"{g}[n={int(v['n'])},gap={v['gap_mean']:+.2f},res={v['resid_mean']:+.2f},{v['class']}]" for g, v in mem)
        rows.append(row)
    pd.DataFrame(rows).to_csv(HERE / 'cards_named.csv', index=False, float_format='%.3f')
    json.dump(out, open(HERE / 'summary.json', 'w'), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == '__main__':
    main()
