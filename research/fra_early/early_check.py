"""User-requested early look at FRA (17Lands card + colour ratings, 2026-09-29 to fetch date).
Compares the published サキヨミ forecast (frozen before release) with early numbers. Indicative only;
the pre-registered scoring stays on the 28-day Public Game Data (research/PENDING_FRA.md)."""
import gzip, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr

HERE = Path(__file__).resolve().parent
PAGES = Path(sys.argv[1] if len(sys.argv) > 1 else '/home/claude/limited-forecast-pages')
raw = json.load(open(HERE / 'raw/card_ratings.json'))
col = json.load(open(HERE / 'raw/color_ratings.json'))
meta = json.load(open(HERE / 'raw/meta.json'))
F = json.load(gzip.open(PAGES / 'public/forecast.json.gz'))['forecast']

fc = pd.DataFrame([{'id': c['id'], 'name': c['name'], 'rarity': c['rarity'], 'colors': ''.join(c['colors']),
                    'gih_pred': float(c['gih']), 'lo': float(c['gih_range'][0]), 'hi': float(c['gih_range'][1]),
                    'alsa_pred': float(c['alsa']), 'type_line': c['type_line']} for c in F['cards']])
ob = pd.DataFrame([{'name': r['name'], 'gih_obs': None if r['ever_drawn_win_rate'] is None else r['ever_drawn_win_rate'] * 100,
                    'gih_n': r['ever_drawn_game_count'], 'alsa_obs': r['avg_seen'], 'seen': r['seen_count']} for r in raw])
# 17Lands may use "A // B" names
ob['key'] = ob['name'].str.split(' // ').str[0]
d = fc.merge(ob, left_on='name', right_on='key', how='left', suffixes=('', '_17l'))
res = {'fetched': meta, 'n_forecast': len(fc), 'unmatched_forecast': d.loc[d['gih_n'].isna(), 'name'].tolist()}

g = d[d['gih_obs'].notna()].copy()
p = g['gih_obs'] / 100
g['se'] = np.sqrt(p * (1 - p) / g['gih_n']) * 100
err = g['gih_pred'] - g['gih_obs']
off = err.mean()
# expected MAE if forecast error (sd s) and sampling noise add: E|N(0, s^2+se^2)| ; compare with 28-day backtest 2.396
rng = np.random.default_rng(0)
res['gih'] = {
    'n_cards': int(len(g)), 'median_games': float(g['gih_n'].median()),
    'obs_mean': float(g['gih_obs'].mean()), 'pred_mean': float(g['gih_pred'].mean()), 'mean_offset_pred_minus_obs': float(off),
    'mae_raw': float(err.abs().mean()), 'mae_offset_removed': float((err - off).abs().mean()),
    'spearman': float(spearmanr(g['gih_pred'], g['gih_obs']).correlation),
    'pearson': float(pearsonr(g['gih_pred'], g['gih_obs'])[0]),
    'sampling_se_median_pp': float(g['se'].median()),
    'range80_coverage_raw': float(((g['gih_obs'] >= g['lo']) & (g['gih_obs'] <= g['hi'])).mean()),
    'range80_coverage_offset_removed': float(((g['gih_obs'] + off >= g['lo']) & (g['gih_obs'] + off <= g['hi'])).mean()),
}
# backtest-equivalent: what MAE would the 28-day backtest error (2.396 pp MAE -> sd ~ 2.396*sqrt(pi/2)) give once early sampling noise is added?
s_bt = 2.396 * np.sqrt(np.pi / 2)
sim = np.mean([np.abs(rng.normal(0, np.sqrt(s_bt**2 + g['se'].values**2))).mean() for _ in range(2000)])
res['gih']['expected_mae_if_backtest_quality_plus_noise'] = float(sim)
by_r = {}
for r, s in g.groupby('rarity'):
    e = s['gih_pred'] - s['gih_obs'] - off
    by_r[r] = {'n': int(len(s)), 'mae_offset_removed': float(e.abs().mean()), 'mean_bias': float(e.mean())}
res['gih']['by_rarity'] = by_r

a = d[d['alsa_obs'].notna() & (d['seen'] >= 200)]
res['alsa'] = {'n_cards': int(len(a)), 'mae': float((a['alsa_pred'] - a['alsa_obs']).abs().mean()),
               'spearman': float(spearmanr(a['alsa_pred'], a['alsa_obs']).correlation), 'backtest_mae': 0.9508}

# deck colours: unsplashed two-colour
pairs = {r['short_name']: r for r in col if not r['is_summary'] and isinstance(r['short_name'], str) and len(r['short_name']) == 2}
alias = {'GW': 'WG', 'RW': 'WR', 'GU': 'UG', 'BG': 'BG', 'RG': 'RG'}
rows = []
for row in F['deck_color']['rows']:
    o = pairs[row['pair']]
    wr = o['wins'] / o['games'] * 100
    rows.append({'pair': row['pair'], 'pred': row['predicted_wr_pct'], 'pred_rank': row['rank'], 'obs': wr, 'games': o['games'],
                 'in_range80': row['range80'][0] <= wr <= row['range80'][1]})
dc = pd.DataFrame(rows)
dc['obs_rank'] = dc['obs'].rank(ascending=False).astype(int)
dc['obs_delta'] = dc['obs'] - dc['obs'].mean()
dc['pred_delta'] = dc['pred'] - dc['pred'].mean()
res['deck_color'] = {'rows': dc.round(3).to_dict('records'),
                     'spearman': float(spearmanr(dc['pred'], dc['obs']).correlation),
                     'mae_raw': float((dc['pred'] - dc['obs']).abs().mean()),
                     'mae_delta': float((dc['pred_delta'] - dc['obs_delta']).abs().mean()),
                     'range80_coverage': float(dc['in_range80'].mean()),
                     'obs_spread_sd': float(dc['obs'].std()), 'pred_spread_sd': float(dc['pred'].std())}

g['err_c'] = g['gih_pred'] - g['gih_obs'] - off
big = g.reindex(g['err_c'].abs().sort_values(ascending=False).index).head(15)
res['largest_misses'] = big[['name', 'rarity', 'colors', 'gih_pred', 'gih_obs', 'gih_n', 'err_c']].round(2).to_dict('records')
g[['name', 'rarity', 'colors', 'gih_pred', 'lo', 'hi', 'gih_obs', 'gih_n', 'err_c']].round(3).to_csv(HERE / 'cards.csv', index=False)
json.dump(res, open(HERE / 'result.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k not in ('largest_misses',)}, indent=1, ensure_ascii=False)[:6000])
print(pd.DataFrame(res['largest_misses']).to_string())
