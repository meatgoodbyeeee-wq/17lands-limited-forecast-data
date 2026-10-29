#!/usr/bin/env python3
"""FRA prospective checks, items 1-12 of research/PENDING_FRA.md (+ items 11, 12 from branches). Scored ONCE.

  python3 research/fra_check/score_fra.py      (from the repository root)  -> research/fra_check/result.json

Actuals (user decision 2026-10-29, deviation from the pre-registration): 17Lands Card Data and Color Ratings for
Premier Draft 2026-09-29..10-26 (final), because Public Game Data only has the file of 2026-10-19 and S3 returns 403.
Cards: fra_actual_gih500.csv (>= 500 GIH games), made once. Pairs: Color Ratings, non-splash two-colour decks, centred on the 10-pair mean.
Every frozen file is checked against its recorded sha256 first; nothing is refitted.
"""
import gzip, hashlib, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

R = Path('research'); H = R / 'fra_check'; FB = H / 'frozen_branch_files'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
SHA = {  # recorded at freeze time
    R / 'gih_llm_extract/fra_frozen_predictions.csv': json.load(open(R / 'gih_llm_extract/fra_frozen_predictions.json'))['sha256'],
    R / 'case2_pairwise/fra_frozen.csv': '9d1d0e692764f91f353913b775647cceb4db881c389a5e8f19f9cfdfd65d309b',
    R / 'c4_fine_effects/fra_frozen_predictions.csv': json.load(open(R / 'c4_fine_effects/fra_frozen_predictions.json'))['sha256'],
    R / 'c5_atomic_effects/fra_frozen_predictions.csv': json.load(open(R / 'c5_atomic_effects/fra_frozen_predictions.json'))['sha256'],
    R / 'c9_power_questions/fra_frozen_predictions.csv': json.load(open(R / 'c9_power_questions/fra_frozen_predictions.json'))['sha256'],
    R / 'd9_colour_strength/fra_frozen_pairs.csv': json.load(open(R / 'd9_colour_strength/fra_frozen_pairs.json'))['sha256'],
    R / 'd10_fra_set_reading/fra_frozen_ai_pairs.csv': json.load(open(R / 'd10_fra_set_reading/fra_frozen_ai_pairs.json'))['sha256'],
    FB / 'g2_bias_spread__fra_frozen_predictions.csv': '54a7ed7ab51c0d4409a51a0680c1d1be4c8a92a79762ef54ef7a8d736b797ffe',
    FB / 'fra_b10_range__fra_b10_range.json': 'aefd48005fa868f5c47f6e672e324b85243c1ad9e22fe6e63bb061ea56af8c46',
}
for p, h in SHA.items():
    assert sha(p) == h, f'{p} changed after freezing'

act = pd.read_csv(H / 'fra_actual_gih500.csv')            # name, gih (pp), gih_n
A = act.set_index('name')['gih']


def card(df, col, scale=1.0):
    d = df[df['name'].isin(A.index)].copy()
    p, a = d[col] * scale, A.loc[d['name']].to_numpy()
    e = p.to_numpy() - a
    top = p.rank(ascending=False, pct=True).to_numpy() <= 0.10
    return {'n': int(len(d)), 'mae_pp': float(np.abs(e).mean()), 'spearman': float(spearmanr(p, a).correlation),
            'mean_a_minus_p_pp': float(-e.mean()), 'pred_top10pct_a_minus_p_pp': float(-e[top].mean())}


def vs(new, old):
    return {'mae_better': new['mae_pp'] < old['mae_pp'], 'spearman_better': new['spearman'] > old['spearman'],
            'mae_diff_pp': new['mae_pp'] - old['mae_pp'], 'spearman_diff': new['spearman'] - old['spearman']}


out = {'actual': {'source': '17Lands Card Data + Color Ratings, PremierDraft 2026-09-29..2026-10-26 (final)', 'deviation':
                  'pre-registered Public Game Data not complete (file of 2026-10-19, S3 403); user chose aggregated 17Lands data 2026-10-29',
                  'cards_ge500': int(len(act)), 'actual_csv_sha256': sha(H / 'fra_actual_gih500.csv')}, 'sha256_verified': True}

# 1 C3
f1 = pd.read_csv(R / 'gih_llm_extract/fra_frozen_predictions.csv')
i1 = {'baseline21': card(f1, 'pred_baseline21_pp'), 'C3': card(f1, 'pred_c3_pp')}
i1['C3_vs_baseline21'] = vs(i1['C3'], i1['baseline21']); i1['supported'] = all(v for k, v in i1['C3_vs_baseline21'].items() if k.endswith('better'))
out['1_C3'] = i1
# 2, 3 Case 2 / 2b
f2 = pd.read_csv(R / 'case2_pairwise/fra_frozen.csv')
i2 = {c: card(f2, c) for c in ['pred_gih', 'adj_w0.3', 'adj2b_w0.3']}
i2['case2_vs_prod'] = vs(i2['adj_w0.3'], i2['pred_gih']); i2['case2b_vs_prod'] = vs(i2['adj2b_w0.3'], i2['pred_gih'])
i2['rule_P_FRA_case2b_supported'] = i2['case2b_vs_prod']['mae_better'] and i2['case2b_vs_prod']['spearman_better']
out['2_3_case2'] = i2
# 4 hosers (per card)
f4 = pd.read_csv(FB / 'hoser_mixture__fra_frozen.csv')
out['4_hosers'] = [{'name': r.name, 'actual': float(A.get(r.name, np.nan)), 'n_ok': bool(r.name in A.index),
                    'published_err': float(r.published - A.get(r.name, np.nan)), 'adjusted_err': float(r.adjusted - A.get(r.name, np.nan))}
                   for r in f4.itertuples()]
# 5 production + range
ad = json.loads(gzip.open(FB / 'pages__adopted-gih-fra.json.gz', 'rt').read())
rg = json.loads((FB / 'pages__gih-range-fra.json').read_text())
prod = pd.DataFrame(ad['cards'])[['id', 'name', 'gih']].merge(pd.DataFrame(rg['cards'])[['id', 'radius']], on='id')


def coverage(df, pcol, rarity):
    d = df[df['name'].isin(A.index)].copy()
    d['a'] = A.loc[d['name']].to_numpy()
    d['in'] = (d['a'] >= d[pcol] - d['radius']) & (d['a'] <= d[pcol] + d['radius'])
    d['rar'] = d['id'].map(rarity)
    return {'n': int(len(d)), 'coverage': float(d['in'].mean()), 'mean_width_pp': float(2 * d['radius'].mean()),
            'by_rarity': {k: float(g['in'].mean()) for k, g in d.groupby('rar')}}


rar = pd.read_csv(R / 'gih_llm_extract/fra_frozen_predictions.csv').set_index('id')['rarity']
out['5_production'] = {'version': ad['version'], 'card': card(prod, 'gih'), 'range80': coverage(prod, 'gih', rar)}
# 6, 7, 10 C4 / C5 / C9
f9 = pd.read_csv(R / 'c9_power_questions/fra_frozen_predictions.csv')
f4c = pd.read_csv(R / 'c4_fine_effects/fra_frozen_predictions.csv')
f5c = pd.read_csv(R / 'c5_atomic_effects/fra_frozen_predictions.csv')
assert np.allclose(f9.pred_A, f5c.pred_A) and np.allclose(f9.pred_B5, f5c.pred_B5) and np.allclose(f4c.pred_B, f5c.pred_B)
m = {c: card(f9, c, 100) for c in ['pred_A', 'pred_B', 'pred_B5', 'pred_B10']}
out['6_C4'] = {'A': m['pred_A'], 'B': m['pred_B'], 'B_vs_A': vs(m['pred_B'], m['pred_A'])}
out['6_C4']['supported'] = out['6_C4']['B_vs_A']['mae_better'] and out['6_C4']['B_vs_A']['spearman_better']
out['7_C5'] = {'B5': m['pred_B5'], 'B5_vs_B': vs(m['pred_B5'], m['pred_B']), 'B5_vs_A': vs(m['pred_B5'], m['pred_A'])}
out['7_C5']['supported'] = all(out['7_C5'][k][j] for k in ('B5_vs_B', 'B5_vs_A') for j in ('mae_better', 'spearman_better'))
out['10_C9'] = {'B10': m['pred_B10'], 'B10_vs_B5': vs(m['pred_B10'], m['pred_B5']), 'B10_vs_A': vs(m['pred_B10'], m['pred_A'])}
out['10_C9']['supported'] = all(out['10_C9'][k][j] for k in ('B10_vs_B5', 'B10_vs_A') for j in ('mae_better', 'spearman_better'))
# 11 B10S
f11 = pd.read_csv(FB / 'g2_bias_spread__fra_frozen_predictions.csv')
assert np.allclose(f11.pred_B10, f9.pred_B10)
b10s = card(f11, 'pred_B10S', 100)
out['11_B10S'] = {'B10S': b10s, 'B10S_vs_B10': vs(b10s, m['pred_B10']), 'supported': b10s['mae_pp'] < m['pred_B10']['mae_pp']}
# 12 B10 range
r12 = json.loads((FB / 'fra_b10_range__fra_b10_range.json').read_text())
b10r = f9[['id', 'name', 'pred_B10']].assign(pred_B10=lambda x: x.pred_B10 * 100).merge(pd.DataFrame(r12['cards'])[['id', 'radius']], on='id')
out['12_B10_range'] = {'B10_range80': coverage(b10r, 'pred_B10', rar), 'production_range80': out['5_production']['range80'], 'target': 0.8}

# 8, 9 colour pairs
cr = json.loads((H / 'fra-actual-color-ratings.json').read_text())
assert cr['final'] and not cr['splash'] and cr['window_end'] == '2026-10-26'
y = pd.Series({k: v['wr_pct'] for k, v in cr['pairs'].items()}); y = y - y.mean()
p8 = pd.read_csv(R / 'd9_colour_strength/fra_frozen_pairs.csv').set_index('pair')
p9 = pd.read_csv(R / 'd10_fra_set_reading/fra_frozen_ai_pairs.csv').set_index('pair')
t = pd.read_csv(R / 'd9_colour_strength/pair_table.csv')
k0 = float(t['F0'] @ t['y'] / (t['F0'] @ t['F0']))        # F0 -> pp scale fitted on the 26 training sets (deck_model.loso_scale)
yy = y.loc[p8.index]
z = lambda s: (s - s.mean()) / s.std(ddof=0)
rho = lambda s: float(spearmanr(s, yy).correlation)
out['8_pairs'] = {'actual_centred_pp': yy.round(3).to_dict(), 'F0_scale_26sets': k0,
                  'D_B5': {'spearman': rho(p8.pred_D_B5), 'mae_pp': float((p8.pred_D_B5 - yy).abs().mean())},
                  'F0_A': {'spearman': rho(p8.F0_A), 'mae_pp': float((p8.F0_A * k0 - yy).abs().mean())},
                  'zero_prediction_mae_pp': float(yy.abs().mean())}
comb = (z(p9.pred_AI) + z(p8.pred_D_B5.loc[p9.index])) / 2
out['9_AI_pairs'] = {'pred_AI': rho(p9.pred_AI.loc[p8.index]), 'pred_D_B5': rho(p8.pred_D_B5), 'F0_A': rho(p8.F0_A),
                     'mean_z_AI_DB5': rho(comb.loc[p8.index]),
                     'ranks': pd.DataFrame({'actual': yy.rank(ascending=False), 'AI': p9.pred_AI.rank(ascending=False),
                                            'D_B5': p8.pred_D_B5.rank(ascending=False), 'F0_A': p8.F0_A.rank(ascending=False)}).astype(int).to_dict()}
(H / 'result.json').write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float) + '\n')
print(json.dumps(out, indent=1, ensure_ascii=False, default=float))
