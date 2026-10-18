"""H1 analysis (Rule F19, see PLAN.md). python3 h1.py"""
import json, re
from pathlib import Path
import numpy as np, pandas as pd
H = Path(__file__).resolve().parent; A2 = H.parent / 'a2_forced_deck_ev'
LINE = re.compile(r'#?([A-Z0-9_]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\|?\s*(.*)')
sub = pd.read_csv(H / 'subset.csv')


def load(d):
    rows = []
    for r in sub.itertuples():
        p = d / f'{r.name}.txt'; m = LINE.match(p.read_text().strip()) if p.exists() else None
        if m and m.group(1) in (str(r.id), r.name):
            rows.append({'name': r.name, 'off': float(m.group(2)), 'on': float(m.group(3)), 'p': float(m.group(4)) / 100})
    x = pd.DataFrame(rows); x['ev'] = x.p * x.on + (1 - x.p) * x.off; return x.set_index('name')


def main():
    j = pd.read_csv(A2 / 'deck_judgements.csv').set_index('name').loc[sub.name]
    runs = {'run1': j[['off', 'on', 'p', 'ev']], 'run2': load(H / 'out_opus2'), 'haiku': load(H / 'out_haiku')}
    print({k: len(v) for k, v in runs.items()})
    act = pd.read_csv(H.parent / 'c9_power_questions/oof_B10.csv.gz'); act['key'] = act.set + '|' + act.name
    act = act.set_index('key'); act['c'] = act.actual_gih - act.groupby('set').actual_gih.transform('mean')
    sk = sub.drop_duplicates(['set', 'id']).set_index(['set', 'id'])['key']
    res = {'n': {k: len(v) for k, v in runs.items()}}
    def pair(a, b):
        idx = runs[a].index.intersection(runs[b].index); o = {}
        for c in ['off', 'on', 'p', 'ev']:
            x, y = runs[a].loc[idx, c], runs[b].loc[idx, c]
            o[c] = {'pearson': float(x.corr(y)), 'spearman': float(x.corr(y, method='spearman')), 'mad': float((x - y).abs().mean()), 'bias': float((y - x).mean())}
        cm = lambda r: r.loc[idx].groupby(sub.set_index('name').loc[idx].key).ev.mean()
        o['card_ev_mad'] = float((cm(runs[a]) - cm(runs[b])).abs().mean()); o['n'] = len(idx); return o
    res['run1_vs_run2'] = pair('run1', 'run2'); res['run1_vs_haiku'] = pair('run1', 'haiku'); res['run2_vs_haiku'] = pair('run2', 'haiku')
    dk = sub.set_index('name').key
    def cardev(*rs):
        idx = set.intersection(*[set(runs[r].index) for r in rs]); m = sum(runs[r].loc[sorted(idx), 'ev'] for r in rs) / len(rs)
        return m.groupby(dk.loc[sorted(idx)]).mean()
    res['card_corr_actual'] = {}
    for lab, rs in [('run1', ['run1']), ('run2', ['run2']), ('haiku', ['haiku']), ('mean12', ['run1', 'run2']), ('mean123', ['run1', 'run2', 'haiku'])]:
        try: e = cardev(*rs)
        except Exception: continue
        a = act.loc[e.index, 'c']; res['card_corr_actual'][lab] = {'pearson': float(e.corr(a)), 'spearman': float(e.corr(a, method='spearman')), 'n': len(e)}
    def on(r, k):
        s = runs[r]; ids = sub[sub.key == k].name; return float(s.loc[s.index.intersection(ids), 'on'].mean())
    res['on_gap_rite_minus_aa'] = {r: on(r, 'FDN|Rite of the Dragoncaller') - on(r, 'MSH|Avengers Assemble!') for r in runs}
    f = res['run1_vs_run2']; hh = res['run1_vs_haiku']; c = res['card_corr_actual']
    res['rule_f19'] = {'opus_reproducible': bool(f['ev']['spearman'] >= .75 and f['card_ev_mad'] <= .5),
                       'haiku_acceptable': bool(hh['ev']['spearman'] >= f['ev']['spearman'] - .05 and abs(hh['on']['bias']) <= 1 and 'haiku' in c and c['haiku']['pearson'] >= c['run1']['pearson'] - .05),
                       'averaging_helps': bool('mean12' in c and c['mean12']['pearson'] >= max(c['run1']['pearson'], c['run2']['pearson']) + .03)}
    json.dump(res, open(H / 'result.json', 'w'), indent=1); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
