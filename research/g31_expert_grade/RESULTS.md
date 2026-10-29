# G3.1 pilot results (2026-10-28): FAIL (C/U improved, rares got worse, net ≈ G3)

Pass agreement 0.94–0.95 (G3: 0.77–0.94). FRA pass 2 and ECL pass 1 re-run (see PLAN.md notes).

| set | Spearman with B5 residual: G3.1 / G3 / C9 / expert | Spearman with actual: G3.1 / G3 / C9 / expert |
|---|---|---|
| FRA | 0.201 / 0.211 / 0.168 / 0.384 | 0.513 / 0.517 / 0.438 / 0.624 |
| TMT | −0.010 / −0.023 / −0.187 / 0.310 | 0.412 / 0.367 / 0.193 / 0.591 |
| ECL | 0.166 / 0.170 / −0.034 / 0.352 | 0.538 / 0.528 / 0.362 / 0.663 |

Within-rarity Spearman with actual (G3.1 / G3): C 0.33/0.28, 0.12/0.09, 0.28/0.11; U 0.50/0.44, 0.15/0.03,
0.32/0.25; R 0.50/0.59, 0.47/0.43, 0.58/0.70; M 0.56/0.60, 0.64/0.55, 0.61/0.42 (FRA, TMT, ECL).
Rule: (a) B5 residual better on 1 of 3 sets ✗; (b) C/U mean +0.081 ≥ 0.05 ✓ → FAIL.

Exploratory (post-hoc): G3.1 for C/U + G3 for R/M gives B5-residual 0.238 / −0.012 / 0.196 and
actual 0.541 / 0.397 / 0.564 — best of the AI variants on FRA and ECL, still well below the expert.
