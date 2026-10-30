#!/usr/bin/env python3
"""Attack test (PLAN_attack_settings.md): per condition, attackers per combat and blocked share (BlockAudit), game length,
draws and timeouts, pair order vs 17Lands, and the Spearman of the decks' instant share with the sim win rate.

  python3 research/forge_sim/atk_metrics.py --forge <forge checkout> NAME=runs/<games>.csv [...]
"""
import argparse, re
from pathlib import Path
import pandas as pd
from scipy.stats import spearmanr
from analyze import PAIRS, pair_wr, actual_pairs

HERE = Path(__file__).resolve().parent


def instant_share(forge):
    out = {}
    for d in sorted((HERE / 'decks_fra_pool_c2u1').glob('*.dck')):
        n = inst = 0
        for line in d.read_text().splitlines():
            m = re.match(r'^(\d+) (.+?)(\|.*)?$', line)
            if not m:
                continue
            name = m.group(2)
            f = Path(forge) / 'forge-gui/res/cardsfolder' / name[0].lower() / (re.sub(r'[^a-z0-9 ]', '', name.lower()).replace(' ', '_') + '.txt')
            types = next((l for l in f.read_text().splitlines() if l.startswith('Types:')), '') if f.exists() else ''
            if 'Land' in types:
                continue
            n += int(m.group(1)); inst += int(m.group(1)) * ('Instant' in types)
        out[d.name.split('_')[1]] = inst / n * 100 if n else float('nan')
    return pd.Series(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--forge', required=True); ap.add_argument('runs', nargs='+')
    a = ap.parse_args()
    y = actual_pairs(HERE / 'actual/fra-color-ratings-splash-combined.json').loc[PAIRS]
    ins = instant_share(a.forge).loc[PAIRS]
    rows, ranks = [], {}
    for spec in a.runs:
        name, path = spec.split('=', 1)
        g = pd.read_csv(path, keep_default_na=False)
        s = pd.read_csv(Path(path).with_name(Path(path).stem + '_seen.csv'), keep_default_na=False)
        b = s[s.zone == 'BlockAudit'].card.str.split('|', expand=True).astype(int)
        turns = s[s.zone != 'BlockAudit'].groupby('game').turns.max()
        t = pair_wr(g)
        ranks[name] = t.wr.rank(ascending=False).astype(int)
        rows.append({'cond': name, 'games': len(g), 'draws': int((g.winner == '').sum()),
                     'timeouts': int(pd.to_numeric(g.timeouts, errors='coerce').fillna(0).sum()),
                     'mean_turns': round(turns.mean(), 2), 'mean_s': round(g.ms.mean() / 1000, 1),
                     'combats_per_game': round(len(b) / len(g), 2), 'attackers_per_combat': round(b[0].mean(), 3),
                     'attackers_per_game': round(b[0].sum() / len(g), 2), 'blocked_share': round(b[1].sum() / b[0].sum() * 100, 1),
                     'rho_vs_17lands': round(spearmanr(t.wr, y).correlation, 3),
                     'rho_instants_vs_wr': round(spearmanr(ins, t.wr).correlation, 3)})
    print(pd.DataFrame(rows).to_string(index=False))
    r = pd.DataFrame(ranks); r['actual'] = y.rank(ascending=False).astype(int); r['instant_pct'] = ins.round(1)
    print(r.to_string())


if __name__ == '__main__':
    main()
