"""A3 simulated P (Rule F17, see PLAN.md).  python3 a3.py sim | arm <B16r|B16a|shuf_B16r|shuf_B16a> | evaluate"""
import importlib.util, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; RES = HERE.parent; A2 = RES / 'a2_forced_deck_ev'
G, H, SEED = 20000, 10, 20261018


def deck(name, cards):
    t = (A2 / 'decks' / f'{name}.txt').read_text()
    main = [int(x) for x in re.findall(r'#(\d+)', t.split('MAIN:')[1].split('\n')[0])]
    basics = sum(int(x) for x in t.split('BASICS:')[1].split('\n')[0].split())
    return main, basics


def enablers(name):
    lines = (A2 / 'enab_out' / f'{name}.txt').read_text().strip().splitlines()
    tm = re.search(r'TARGET\s+#?(\d+)\s+MV\s+(\d+)', lines[0])
    en = []
    for l in lines[1:]:
        m = re.match(r'#?(\d+)\s+MV\s+(\d+)\s+(BEFORE|AFTER|EITHER)', l.strip())
        if m: en.append((int(m.group(1)), int(m.group(2)), m.group(3)))
    return int(tm.group(2)) if tm else None, en


def sim_deck(name, tid, cards, rng):
    main, basics = deck(name, cards)
    gi = cards.set_index('id')
    tmv, en = enablers(name)
    if tmv is None: tmv = int(float(gi.loc[tid].mv))
    if not en: return 1.0, 1.0, np.nan
    slots = main + [-1] * basics
    n = len(slots); land = np.array([s == -1 or 'Land' in str(gi.loc[s]['type']) for s in slots])
    pos = np.argsort(rng.random((G, n)), axis=1).argsort(axis=1)  # pos[g, slot]
    play = rng.random(G) < .5
    seen = np.stack([7 + t - play.astype(int) for t in range(1, H + 1)], 1)  # cards seen by turn t
    landpos = np.where(land[None, :], pos, n + 99)
    mana = np.zeros((G, H), int); prev = np.zeros(G, int)
    for t in range(H):
        ls = (landpos < seen[:, t:t + 1]).sum(1); prev = np.minimum(prev + 1, ls); mana[:, t] = prev
    tslots = [i for i, s in enumerate(slots) if s == tid]
    tp = pos[:, tslots].min(1)
    ok = (seen > tp[:, None]) & (mana >= tmv)
    cast = ok.any(1); tt = np.where(cast, ok.argmax(1), H)
    gidx = np.arange(G); ttc = np.minimum(tt, H - 1); mtt = mana[gidx, ttc]; stt = seen[gidx, ttc]
    wend = np.minimum(tt + 3, H - 1); mw = mana[gidx, wend]; sw = seen[gidx, wend]
    order = {}
    for eid, emv, o in en: order[eid] = (emv, o)
    has_before = any(o == 'BEFORE' for _, _, o in en); has_after = any(o == 'AFTER' for _, _, o in en)
    bef = np.zeros(G, int); aft = np.zeros(G, int)
    tset = set(tslots[:1])
    for i, s in enumerate(slots):
        if s not in order or i in tset: continue
        emv, o = order[s]; p = pos[:, i]
        c_ok = (seen > p[:, None]) & (mana >= emv); ci = np.where(c_ok.any(1), c_ok.argmax(1), H)
        b = (ci < tt) | ((ci <= tt) & (mtt >= emv + tmv))
        a = ((sw > p) & (mw >= emv) & (tt + 1 <= wend)) | ((stt > p) & (mtt - tmv >= emv))
        if o in ('BEFORE', 'EITHER'): bef += b
        if o in ('AFTER', 'EITHER'): aft += a
    cnt = bef if has_before else (aft if has_after else np.maximum(bef, aft))
    cnt = cnt[cast]
    return float((cnt >= 1).mean()), float((cnt >= 2).mean()), float(cast.mean())


def sim():
    cards = pd.read_csv(RES / 'c11_set_reading_synergy/set_cards.csv.gz', keep_default_na=False)
    dj = pd.read_csv(A2 / 'deck_judgements.csv'); rng = np.random.default_rng(SEED); rows = []
    for r in dj.itertuples():
        p1, p2, cr = sim_deck(r.name, r.id, cards[cards.set == r.set], rng)
        rows.append({'name': r.name, 'set': r.set, 'id': r.id, 'off': r.off, 'on': r.on, 'p_judge': r.p,
                     'psim': p1, 'psim2': p2, 'cast_rate': cr, 'evsim': p1 * r.on + (1 - p1) * r.off})
    d = pd.DataFrame(rows); d.to_csv(HERE / 'deck_sim.csv', index=False)
    sel = pd.read_csv(A2 / 'selected.csv')
    f = d.groupby(['set', 'id'])[['off', 'on', 'p_judge', 'psim', 'psim2', 'evsim']].mean().reset_index().merge(sel[['set', 'id', 'key']], on=['set', 'id'])
    f.to_csv(HERE / 'a3_features.csv', index=False); print(f.describe().round(3))


if __name__ == '__main__':
    sim()
