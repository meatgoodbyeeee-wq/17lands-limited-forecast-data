"""I1 build: tiered-ON judge inputs (same ladders as F1) + simulated enabler-count distribution. python3 build.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
H = Path(__file__).resolve().parent; R = H.parent
sys.path.insert(0, str(R / 'a3_simulated_p')); import a3
sub = pd.read_csv(R / 'h1_judge_reliability/subset.csv')
HOLD = 0.5  # share of AFTER-enablers drawn before the target that are still held when it lands


def dist(name, tid, cards, rng):
    """P(0), P(1), P(2), P(3+) enablers working with the target, conditional on the target being cast (A3 model)."""
    main, basics = a3.deck(name, cards); gi = cards.set_index('id'); tmv, en = a3.enablers(name)
    if tmv is None: tmv = int(float(gi.loc[tid].mv))
    if not en: return [0, 1, 0, 0], 1.0
    G, Hh = a3.G, a3.H
    slots = main + [-1] * basics; n = len(slots)
    land = np.array([s == -1 or 'Land' in str(gi.loc[s]['type']) for s in slots])
    pos = np.argsort(rng.random((G, n)), axis=1).argsort(axis=1); play = rng.random(G) < .5
    seen = np.stack([7 + t - play.astype(int) for t in range(1, Hh + 1)], 1)
    landpos = np.where(land[None, :], pos, n + 99); mana = np.zeros((G, Hh), int); prev = np.zeros(G, int)
    for t in range(Hh):
        prev = np.minimum(prev + 1, (landpos < seen[:, t:t + 1]).sum(1)); mana[:, t] = prev
    tslots = [i for i, s in enumerate(slots) if s == tid]; tp = pos[:, tslots].min(1)
    ok = (seen > tp[:, None]) & (mana >= tmv); cast = ok.any(1); tt = np.where(cast, ok.argmax(1), Hh)
    gidx = np.arange(G); ttc = np.minimum(tt, Hh - 1); mtt = mana[gidx, ttc]; stt = seen[gidx, ttc]
    wend = np.minimum(tt + 3, Hh - 1); mw = mana[gidx, wend]; sw = seen[gidx, wend]
    order = {e: (m, o) for e, m, o in en}; hb = any(o == 'BEFORE' for _, _, o in en); ha = any(o == 'AFTER' for _, _, o in en)
    bef = np.zeros(G, int); aft = np.zeros(G, int)
    for i, s in enumerate(slots):
        if s not in order or i == tslots[0]: continue
        emv, o = order[s]; p = pos[:, i]
        c_ok = (seen > p[:, None]) & (mana >= emv); ci = np.where(c_ok.any(1), c_ok.argmax(1), Hh)
        b = (ci < tt) | ((ci <= tt) & (mtt >= emv + tmv))
        held = (p >= stt) | (rng.random(G) < HOLD)  # drawn after the target was cast, or an earlier draw that was held
        a = held & (((sw > p) & (mw >= emv) & (tt + 1 <= wend)) | ((stt > p) & (mtt - tmv >= emv)))
        if o in ('BEFORE', 'EITHER'): bef += b
        if o in ('AFTER', 'EITHER'): aft += a
    cnt = (bef if hb else (aft if ha else np.maximum(bef, aft)))[cast]
    if cast.mean() < .05: return None, float(cast.mean())
    return [float((cnt == 0).mean()), float((cnt == 1).mean()), float((cnt == 2).mean()), float((cnt >= 3).mean())], float(cast.mean())


def main():
    cards = pd.read_csv(R / 'c11_set_reading_synergy/set_cards.csv.gz', keep_default_na=False)
    f1p = None; rng = np.random.default_rng(20261018); rows = []
    for r in sub.itertuples():
        txt = (R / 'f1_ref_anchor/in' / f'{r.name}.txt').read_text(); (H / 'in' / f'{r.name}.txt').write_text(txt)
        d, cr = dist(r.name, r.id, cards[cards.set == r.set], rng)
        rows.append({'name': r.name, 'key': r.key, 'cast_rate': cr, 'fallback': d is None,
                     **({f'w{k}': v for k, v in enumerate(d)} if d else {'w0': np.nan, 'w1': np.nan, 'w2': np.nan, 'w3': np.nan})})
    pd.DataFrame(rows).to_csv(H / 'weights.csv', index=False)
    names = list(sub.name)
    for i in range(0, len(names), 10): (H / 'batches' / f'b{i // 10:02d}.txt').write_text('\n'.join(names[i:i + 10]) + '\n')
    w = pd.DataFrame(rows); print(w[['w0', 'w1', 'w2', 'w3']].describe().round(3)); print('fallback', w.fallback.sum())
    print(w[w.key.isin(['FDN|Rite of the Dragoncaller', 'MSH|Avengers Assemble!', 'TDM|Smile at Death'])].round(3).to_string())


if __name__ == '__main__':
    main()
