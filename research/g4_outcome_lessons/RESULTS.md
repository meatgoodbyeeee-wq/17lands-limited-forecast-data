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
