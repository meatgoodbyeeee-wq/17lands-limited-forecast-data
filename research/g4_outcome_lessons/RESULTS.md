# G4 pilot results (2026-10-29): FAIL (pre-registered rule)
Outcome lessons (35, from B10's largest misses in 11 lesson sets) -> Opus adjustment (pp) per card for whole target set, 1 pass.
| set | cards adjusted | Spearman(adj, B10 residual) | MAE B10 -> combo (k fitted on other 2 sets) | top-decile MAE B10 -> combo |
|---|---|---|---|---|
| FRA | 184/271 | **+0.337** | 2.316 -> 2.332 (k = -0.05) | 4.55 -> 4.63 |
| TMT | 93/188 | +0.121 | 2.552 -> 2.541 | 4.71 -> 4.65 |
| ECL | 107/268 | **-0.119** | 2.345 -> 2.438 | 4.33 -> 3.99 |
Pooled MAE gain -0.038pp (needs >= +0.03) -> FAIL. Spearman > 0.10 on 2/3 sets, but the signal is not consistent: ECL is opposite, so the combination weight learned from two sets fails on the third.
Post-hoc (not for decisions): upward adjustments (>= +1.5pp) had mean residual +1.51 / +0.93 / -0.22 (FRA/TMT/ECL); downward adjustments (<= -1.5pp) had mean residual +0.53 / +0.86 / +1.01, i.e. the "overrated" lessons were wrong on every set. Adjustments correlate 0.23-0.44 with B10's prediction (lesson 1 "stretch the top").
Reading: outcome lessons carry real signal on some sets (FRA strongly) but are set-dependent; as written they are not reliable. Tokens ~0.45M.

## Why the lessons do not help (why/why.py, B10 OOF, all 28 sets)
Mean B10 residual (pp) of cards matching each main lesson — in the 11 lesson sets / the 17 other sets / sets with the lesson's sign:
- top 5% predicted (L1 "stretch the top"): +1.09 / +0.86 / 24 of 28 sets -> the only robust lesson; as a LOSO constant it improves MAE by only 0.005pp.
- bottom 5% (L3): +0.07 / -0.45 / 10 of 28 -> not real.
- plain card draw (L4, claimed +3..+6): +0.41 / +0.02 / 16 of 26.  discard (L5, claimed +3..+9): +0.35 / -0.11 / 10 of 17.  counterspell (L6): +0.91 / +0.20 / 11 of 21.
- the per-set bias of a category varies with SD 1.0-1.6pp, larger than its mean -> set-dependent.
Causes: (1) lessons were mined from the 450 largest misses, so the sizes are ~10x inflated (selection / regression to the mean); (2) the typical miss for a card type is ~0 because B10 already has effect tags (C4/C5); (3) what remains is set-specific (sign flips between sets); (4) Opus applied them widely (184/271 cards in FRA).
