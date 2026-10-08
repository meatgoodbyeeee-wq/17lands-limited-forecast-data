"""Audit perf flags against C5 tags (C5 = independent AI reading). python3 audit.py [TAG n]"""
import re, sys, warnings
import pandas as pd
warnings.filterwarnings('ignore')
sys.path.insert(0, '../c5_atomic_effects')
import check_raw as cr
M = {'DR': ['draw_n'], 'SC': ['select_n', 'loot'], 'TK': ['token_n'], 'CL': ['artifact_token_n'], 'PC': ['counters_n'],
     'PT': ['trick_p', 'trick_t', 'team_pump', 'pump_activated', 'pump_other'], 'AN': ['anthem'], 'EQ': ['aura_equip_p', 'aura_equip_t', 'aura_equip_kw', 'vehicle'],
     'CS': ['counterspell'], 'RC': ['recur_hand', 'recur_bf', 'recur_self'], 'DS': ['discard_opp'], 'MI': ['mill_opp'], 'DL': ['drain_n', 'face_dmg'],
     'RM': ['ramp'], 'FX': ['land_search', 'fixing'], 'CR': ['cost_reduction', 'alt_cost'], 'SK': ['mana_sink'], 'ET': ['etb'], 'DY': ['dies_trigger'],
     'AT': ['attack_trigger'], 'CH': ['modal']}


def run(show=None, n=12):
    raw, _ = cr.load_raw()
    t = pd.read_csv('profiles.csv.gz', keep_default_na=False)
    res = {}
    for tag, cols in M.items():
        cols = [c for c in cols if c in t.columns]
        has = t.id.map(lambda i: raw.get(i, ([], {}))[1].get(tag, 0) > 0)
        got = t[cols].astype(float).sum(axis=1) > 0
        res[tag] = (int(has.sum()), int((has & got).sum()), int((~has & got).sum()))
        if show == tag:
            for r in t[has & ~got].sample(min(n, int((has & ~got).sum())), random_state=n).itertuples():
                print('  -', r.type_line[:22], '|', re.sub(r'\s+', ' ', r.btext)[:260])
    for k, (a, b, c) in res.items():
        print(f'{k}: C5 {a:4d}  caught {b:4d} ({b / max(a, 1):.0%})  flagged-not-C5 {c}')


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else None, int(sys.argv[2]) if len(sys.argv) > 2 else 12)
