#!/usr/bin/env python3
"""Score the 10 items of research/PENDING_FRA.md on FRA 28-day Public Game Data. Read-only on frozen files; nothing is refitted.

  python3 research/fra_check/score_pending.py --gih gih.csv --pairs FRA_pairs.csv --out out.json [--pages-dir DIR] [--hoser-csv FILE]
  python3 research/fra_check/score_pending.py --selftest            # synthetic data only

--gih   : set,card_name,gih_games,gih_wins,gih_wr,gih_wr_pct,window_start,window_end (scripts/aggregate_17lands.py), cards with gih_games >= 500
--pairs : <SET>_pairs.csv of scripts/deck_pair_aggregate.py (set,main_colors,splash,half,games,wins)
Name matching: exact string; if no exact match, the front face (text before " // ") of both sides. Unmatched names are listed.
"""
import argparse, gzip, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = ROOT / 'research'
PAIRS = ["WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG"]
MIN_GAMES = 500
CASE2_SHA = '9d1d0e692764f91f353913b775647cceb4db881c389a5e8f19f9cfdfd65d309b'  # PENDING_FRA.md
HOSER_PATH = 'research/hoser_mixture/fra_frozen.csv'
HOSER_REFS = ['origin/research/hoser-metrics', 'FETCH_HEAD']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_hash(csv, expected, label):
    got = sha(csv)
    if got != expected:
        raise SystemExit(f'HASH MISMATCH {label}: {csv} sha256 {got} != {expected}')
    return got


def meta_hash(csv):
    return json.load(open(Path(csv).with_suffix('.json')))['sha256']


def front(n):
    return str(n).split(' // ')[0].strip()


def match(frozen_names, gih_names):
    """-> dict gih_name -> frozen_name, list of fallback matches, list of unmatched gih names, list of unused frozen names."""
    fz = set(frozen_names)
    ff = {}
    for n in fz:
        ff.setdefault(front(n), []).append(n)
    m, fb, un = {}, [], []
    for g in gih_names:
        if g in fz:
            m[g] = g
        elif len(ff.get(front(g), [])) == 1:
            m[g] = ff[front(g)][0]; fb.append([g, m[g]])
        else:
            un.append(g)
    used = set(m.values())
    return m, fb, un, sorted(fz - used)


def sp(a, b):
    return float(spearmanr(a, b).correlation)


def mae(p, y):
    return float(np.mean(np.abs(np.asarray(p) - np.asarray(y))))


def metr(p, y):
    return {'mae_pp': mae(p, y), 'spearman': sp(p, y)}


def beats(a, b):
    return a['mae_pp'] < b['mae_pp'] and a['spearman'] > b['spearman']


def load_gih(path):
    g = pd.read_csv(path)
    need = ['set', 'card_name', 'gih_games', 'gih_wins', 'gih_wr', 'gih_wr_pct']
    miss = [c for c in need if c not in g.columns]
    if miss:
        raise SystemExit(f'gih csv missing {miss}')
    g = g[g['gih_games'] >= MIN_GAMES].copy()
    if g['card_name'].duplicated().any():
        raise SystemExit('duplicate card_name in gih csv: ' + str(g.loc[g['card_name'].duplicated(), 'card_name'].tolist()[:5]))
    return g.set_index('card_name')['gih_wr_pct']


def card_item(num, title, df, name_col, arms, rule, gih, unmatched, scale=1.0):
    """arms: {label: column}; first arm is the candidate. rule: (candidate, [baselines]) or None (reported only)."""
    m, fb, un, unused = match(df[name_col], gih.index)
    unmatched[f'item{num}'] = {'gih_not_in_frozen': un, 'frozen_not_in_gih': len(unused), 'front_face_matches': fb}
    d = df.set_index(name_col)
    rows = [(g, f) for g, f in m.items()]
    y = np.array([gih[g] for g, _ in rows])
    res = {}
    for lab, col in arms.items():
        p = np.array([d.loc[f, col] for _, f in rows], float) * scale
        if not (30 < np.nanmean(p) < 80):
            raise SystemExit(f'item {num} {col}: mean {np.nanmean(p):.3f} not in pp range; check units')
        res[lab] = metr(p, y)
    out = {'item': num, 'title': title, 'n_cards': len(rows), 'arms': res, 'columns': arms}
    if rule:
        cand, bases = rule
        wins = {b: beats(res[cand], res[b]) for b in bases}
        out['beats'] = wins
        out['verdict'] = 'supported' if all(wins.values()) else 'not supported'
        out['rule'] = f'{cand} beats ' + ' and '.join(bases) + ' on both MAE and within-set Spearman'
    else:
        out['verdict'] = 'reported only'
    return out


def load_hoser(arg):
    if arg:
        return pd.read_csv(arg)
    if not any(subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', '-q', x], capture_output=True).returncode == 0 for x in HOSER_REFS[:1]):
        subprocess.run(['git', '-C', str(ROOT), 'fetch', '--depth', '50', 'origin', 'research/hoser-metrics'], capture_output=True)  # sets FETCH_HEAD
    for ref in HOSER_REFS:
        r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:{HOSER_PATH}'], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.startswith('id,name'):
            import io
            return pd.read_csv(io.StringIO(r.stdout))
    return None


def item4(hoser, gih, unmatched):
    if hoser is None:
        return {'item': 4, 'title': 'Colour-hoser mixture', 'verdict': 'unsupported (hoser-metrics branch not available)'}
    m, fb, un, unused = match(hoser['name'], gih.index)
    unmatched['item4'] = {'gih_not_in_frozen': 'n/a (5 cards only)', 'frozen_not_in_gih': unused, 'front_face_matches': fb}
    h = hoser.set_index('name')
    cards = []
    for g, f in m.items():
        a = float(gih[g]); pub, adj = float(h.loc[f, 'published']), float(h.loc[f, 'adjusted'])
        cards.append({'card': f, 'actual_pp': a, 'published': pub, 'adjusted': adj,
                      'abs_err_published': abs(pub - a), 'abs_err_adjusted': abs(adj - a),
                      'adjusted_closer': abs(adj - a) < abs(pub - a)})
    out = {'item': 4, 'title': 'Colour-hoser mixture (5 hosers)', 'n_cards': len(cards), 'cards': cards,
           'columns': {'candidate': 'adjusted', 'baseline': 'published'}, 'verdict': 'reported only'}
    if cards:
        out['mae_published'] = float(np.mean([c['abs_err_published'] for c in cards]))
        out['mae_adjusted'] = float(np.mean([c['abs_err_adjusted'] for c in cards]))
        out['n_adjusted_closer'] = int(sum(c['adjusted_closer'] for c in cards))
        out['note'] = 'per-card comparison only; no hash recorded for this file; n too small for Spearman'
    return out


def item5(pages, gih, unmatched):
    base = {'item': 5, 'title': 'Production forecast itself (gih-c3-28set-20260929) with 80% range'}
    if not pages:
        return {**base, 'verdict': 'unsupported (Pages repo not given)'}
    pg, pr = Path(pages) / 'data/adopted-gih-fra.json.gz', Path(pages) / 'data/gih-range-fra.json'
    if not (pg.exists() and pr.exists()):
        return {**base, 'verdict': f'unsupported (missing {pg} or {pr})'}
    A = json.load(gzip.open(pg, 'rt', encoding='utf-8'))
    Rg = json.load(open(pr, encoding='utf-8'))
    if A.get('version') != 'gih-c3-28set-20260929':
        raise SystemExit('Pages adopted-gih-fra version is ' + str(A.get('version')))
    a = pd.DataFrame(A['cards'])[['id', 'name', 'gih']]
    r = pd.DataFrame(Rg['cards'])[['id', 'radius']]
    a = a.merge(r, on='id', how='left', validate='one_to_one')
    m, fb, un, unused = match(a['name'], gih.index)
    unmatched['item5'] = {'gih_not_in_frozen': un, 'frozen_not_in_gih': len(unused), 'front_face_matches': fb}
    d = a.set_index('name')
    rows = list(m.items())
    y = np.array([gih[g] for g, _ in rows]); p = np.array([d.loc[f, 'gih'] for _, f in rows], float)
    rad = np.array([d.loc[f, 'radius'] for _, f in rows], float)
    ok = ~np.isnan(rad)
    cov = float(np.mean(np.abs(y[ok] - p[ok]) <= rad[ok])) if ok.any() else None
    return {**base, 'n_cards': len(rows), 'columns': {'pred': 'adopted-gih-fra.json.gz cards[].gih', 'range': 'gih-range-fra.json cards[].radius (range = gih +- radius, per its method note)'},
            **metr(p, y), 'coverage_80': cov, 'target_coverage': Rg.get('target_coverage'), 'n_range_missing': int((~ok).sum()),
            'pages_sha256': {'adopted-gih-fra.json.gz': sha(pg), 'gih-range-fra.json': sha(pr)},
            'verdict': 'reported only'}


def pair_wr(path):
    p = pd.read_csv(path, keep_default_na=False)
    u = p[(~p['splash'].astype(str).str.lower().eq('true')) & p['main_colors'].isin(PAIRS)]
    rows = []
    for pair in PAIRS:
        q = u[u['main_colors'] == pair]
        g, w = q['games'].sum(), q['wins'].sum()
        rows.append({'pair': pair, 'games': int(g), 'wr': w / g * 100 if g else np.nan})
    t = pd.DataFrame(rows)
    if t['wr'].isna().any():
        raise SystemExit('a colour pair has no games in the pairs csv')
    t['y'] = t['wr'] - t['wr'].mean()   # centred like research/deck_pair
    return t


def zs(x):
    x = np.asarray(x, float); return (x - x.mean()) / x.std(ddof=0)


def items89(pairs_csv, f8, f9):
    pt = pd.read_csv(R / 'd9_colour_strength/pair_table.csv')   # 26 training sets (frozen data, read only)
    scale = float((pt['F0'] * pt['y']).sum() / (pt['F0'] ** 2).sum())   # d9 dm.loso_scale: through-origin slope, here on all 26 sets
    t = pair_wr(pairs_csv).merge(pd.read_csv(f8), on='pair').merge(pd.read_csv(f9)[['pair', 'pred_AI']], on='pair')
    assert len(t) == 10
    y = t['y'].to_numpy()
    sc = t['F0_A'] * scale
    r8 = {'pred_D_B5': {'spearman': sp(t['pred_D_B5'], y), 'mae_pp': mae(t['pred_D_B5'], y)},
          'F0_A': {'spearman': sp(t['F0_A'], y), 'mae_pp': mae(sc, y)}}
    i8 = {'item': 8, 'title': 'Colour-pair strength D_B5', 'n_pairs': 10, 'arms': r8, 'verdict': 'reported only',
          'columns': {'pred': 'pred_D_B5', 'baseline': 'F0_A', 'target': 'centred non-splash pair win rate (pp)'},
          'scale': f'pred_D_B5 is already in pp (ridge fitted on centred pair WR of 26 sets, d9/freeze_fra.py). F0_A scaled by through-origin slope {scale:.4f} = sum(F0*y)/sum(F0^2) over the 260 rows of d9_colour_strength/pair_table.csv (d9 dm.loso_scale, fitted on all 26 sets instead of leave-one-out).'}
    z = (zs(t['pred_AI']) + zs(t['pred_D_B5'])) / 2
    r9 = {k: {'spearman': sp(t[k], y), 'mae_pp': None} for k in ['pred_AI', 'pred_D_B5', 'F0_A']}
    r9['z_mean(pred_AI,pred_D_B5)'] = {'spearman': sp(z, y), 'mae_pp': None}
    i9 = {'item': 9, 'title': 'AI reading of FRA (D10)', 'n_pairs': 10, 'arms': r9, 'verdict': 'reported only',
          'columns': {'pred': 'pred_AI', 'baselines': 'pred_D_B5, F0_A', 'combo': 'mean of within-set z-scores (population sd) of pred_AI and pred_D_B5'},
          'mae_note': 'MAE not specified for item 9 and pred_AI (0-10 score) has no scale in the PLAN; left blank. See item 8 for pred_D_B5 and F0_A MAE.'}
    return i8, i9, t[['pair', 'games', 'wr', 'y']].round(4).to_dict('records')


def run(gih_csv, pairs_csv, pages, hoser_csv, selftest=False):
    hashes = {}
    f1, f2, f6, f7, f8, f10 = [R / x for x in ['gih_llm_extract/fra_frozen_predictions.csv', 'case2_pairwise/fra_frozen.csv',
                               'c4_fine_effects/fra_frozen_predictions.csv', 'c5_atomic_effects/fra_frozen_predictions.csv',
                               'd9_colour_strength/fra_frozen_pairs.csv', 'c9_power_questions/fra_frozen_predictions.csv']]
    f9 = R / 'd10_fra_set_reading/fra_frozen_ai_pairs.csv'
    for lab, f in [('item1', f1), ('item6', f6), ('item7', f7), ('item8', f8), ('item9', f9), ('item10', f10)]:
        hashes[lab] = check_hash(f, meta_hash(f), lab)
    hashes['item2_3'] = check_hash(f2, CASE2_SHA, 'item2_3')
    gih = load_gih(gih_csv)
    un, items = {}, []
    c = lambda *a, **k: card_item(*a, **k, gih=gih, unmatched=un)
    d1 = pd.read_csv(f1)
    items.append(c(1, 'Case 1: C3 LLM features', d1, 'name', {'c3': 'pred_c3_pp', 'baseline21': 'pred_baseline21_pp'}, ('c3', ['baseline21'])))
    d2 = pd.read_csv(f2)
    items.append(c(2, 'Case 2: BT rankings (adj_w0.3)', d2, 'name', {'adj_w0.3': 'adj_w0.3', 'pred_gih': 'pred_gih'}, None))
    items.append(c(3, 'Case 2b: debiased BT (adj2b_w0.3), Rule P-FRA', d2, 'name', {'adj2b_w0.3': 'adj2b_w0.3', 'pred_gih': 'pred_gih'}, ('adj2b_w0.3', ['pred_gih'])))
    items.append(item4(load_hoser(hoser_csv), gih, un))
    items.append(item5(pages, gih, un))
    items.append(c(6, 'C4 finer card effects, Rule F', pd.read_csv(f6), 'name', {'B': 'pred_B', 'A': 'pred_A'}, ('B', ['A']), scale=100))
    items.append(c(7, 'C5 atomic effects, Rule F5', pd.read_csv(f7), 'name', {'B5': 'pred_B5', 'B': 'pred_B', 'A': 'pred_A'}, ('B5', ['B', 'A']), scale=100))
    i8, i9, pw = items89(pairs_csv, f8, f9)
    items += [i8, i9]
    items.append(c(10, 'C9 power questions x3, Rule F10', pd.read_csv(f10), 'name', {'B10': 'pred_B10', 'B5': 'pred_B5', 'A': 'pred_A'}, ('B10', ['B5', 'A']), scale=100))
    items.sort(key=lambda i: i['item'])
    return {'matching_rule': 'exact name; else front face (text before " // ") of both sides when unique; others listed in unmatched',
            'n_gih_cards': int(len(gih)), 'frozen_sha256_checked': hashes, 'unmatched': un, 'pair_wr': pw, 'items': items}


def show(res):
    for i in res['items']:
        print(f"#{i['item']:>2} {i['title']}: {i['verdict']}")
        for k, v in (i.get('arms') or {}).items():
            print(f"      {k:28s} MAE {v['mae_pp'] if v['mae_pp'] is None else round(v['mae_pp'], 3)}  rho {v['spearman']:.3f}")
        if 'coverage_80' in i:
            print(f"      MAE {i['mae_pp']:.3f} rho {i['spearman']:.3f} coverage {i['coverage_80']}")
    print('unmatched gih names:', {k: v['gih_not_in_frozen'] for k, v in res['unmatched'].items()})


def selftest():
    rng = np.random.default_rng(1)
    names = pd.read_csv(R / 'case2_pairwise/fra_frozen.csv')['name'].tolist()
    tmp = Path(tempfile.mkdtemp(prefix='fra_selftest_'))
    gnames = list(names)
    gnames[0] = gnames[0] + ' // Back Face'        # DFC naming differs -> front-face fallback
    gnames[1] = gnames[1] + ' (X)'                 # truly unmatched
    g = pd.DataFrame({'set': 'FRA', 'card_name': gnames, 'gih_games': rng.integers(500, 9000, len(names))})
    g['gih_wins'] = (g['gih_games'] * rng.uniform(.5, .62, len(g))).astype(int)
    g['gih_wr'] = g['gih_wins'] / g['gih_games']; g['gih_wr_pct'] = g['gih_wr'] * 100
    g['window_start'] = '2026-09-29'; g['window_end'] = '2026-10-26'
    g = pd.concat([g, pd.DataFrame([{'set': 'FRA', 'card_name': 'Low Sample', 'gih_games': 100, 'gih_wins': 50, 'gih_wr': .5, 'gih_wr_pct': 50, 'window_start': '', 'window_end': ''}])])
    g.to_csv(tmp / 'gih.csv', index=False)
    rows = []
    for pair in PAIRS:
        for sp_ in (False, True):
            for h in (0, 1):
                n = int(rng.integers(500, 3000)); rows.append({'set': 'FRA', 'main_colors': pair, 'splash': sp_, 'half': h, 'games': n, 'wins': int(n * rng.uniform(.5, .6))})
    rows.append({'set': 'FRA', 'main_colors': 'WUB', 'splash': False, 'half': 0, 'games': 100, 'wins': 50})
    pd.DataFrame(rows).to_csv(tmp / 'pairs.csv', index=False)
    pg = tmp / 'pages/data'; pg.mkdir(parents=True)
    cards = [{'id': str(i), 'name': n, 'gih': 55 + float(rng.normal(0, 2))} for i, n in enumerate(names)]
    with gzip.open(pg / 'adopted-gih-fra.json.gz', 'wt', encoding='utf-8') as f:
        json.dump({'version': 'gih-c3-28set-20260929', 'cards': cards}, f)
    json.dump({'target_coverage': 0.8, 'cards': [{'id': c['id'], 'radius': 4.0} for c in cards]}, open(pg / 'gih-range-fra.json', 'w'))
    hz = pd.DataFrame({'id': 'x', 'name': names[2:7], 'published': 55.0, 'adjusted': 54.0})
    hz.to_csv(tmp / 'hoser.csv', index=False)
    res = run(tmp / 'gih.csv', tmp / 'pairs.csv', tmp / 'pages', tmp / 'hoser.csv', True)
    show(res)
    ok = len(res['items']) == 10
    for i in res['items']:
        ok &= i['verdict'] in ('supported', 'not supported', 'reported only')
    miss = res['unmatched']['item1']
    ok &= miss['gih_not_in_frozen'] == [gnames[1]] and len(miss['front_face_matches']) == 1
    r5 = [i for i in res['items'] if i['item'] == 5][0]
    ok &= r5['coverage_80'] is not None and 'Low Sample' not in miss['gih_not_in_frozen']
    # absent pages -> unsupported, no crash
    res2 = run(tmp / 'gih.csv', tmp / 'pairs.csv', None, None, True)
    ok &= [i for i in res2['items'] if i['item'] == 5][0]['verdict'].startswith('unsupported')
    # tampered frozen hash must stop: simulate by checking a wrong expected value
    try:
        check_hash(R / 'case2_pairwise/fra_frozen.csv', '0' * 64, 'x'); ok = False
    except SystemExit:
        pass
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gih'); ap.add_argument('--pairs'); ap.add_argument('--out', type=Path)
    ap.add_argument('--pages-dir'); ap.add_argument('--hoser-csv'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.gih and a.pairs and a.out):
        ap.error('--gih, --pairs and --out are required')
    res = run(a.gih, a.pairs, a.pages_dir, a.hoser_csv)
    a.out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    show(res)


if __name__ == '__main__':
    main()
