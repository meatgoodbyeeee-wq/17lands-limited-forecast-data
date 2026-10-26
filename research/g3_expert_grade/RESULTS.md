# G3 pilot results (2026-10-27): FAIL on the pre-registered rule, clear partial progress

| set | Spearman with actual: G3 / C9 GRADE / expert / B10 | Spearman(·, B10 residual): G3 / C9 | Spearman(·, expert): G3 / C9 | ok |
|---|---|---|---|---|
| FRA | **0.517** / 0.438 / 0.624 / 0.604 | 0.138 / 0.061 | **0.648** / 0.454 | no (resid < 0.15) |
| TMT | **0.367** / 0.193 / 0.591 / 0.487 | −0.048 / −0.236 | **0.618** / 0.352 | no |
| ECL | **0.528** / 0.362 / 0.663 / 0.595 | 0.119 / −0.104 | **0.694** / 0.461 | no (resid < 0.15) |

- G3 beats the current AI GRADE (C9) on every set: +0.08 / +0.17 / +0.17 Spearman with actual,
  and imitates the expert much better (0.65–0.69 vs 0.35–0.46).
- But it does not yet carry enough information beyond B10: residual correlation 0.14 / −0.05 / 0.12
  (expert grades themselves: ~0.25–0.36). Pre-registered rule needs > 0.15 on 2 of 3 → FAIL.
- Reported (combination fitted on the other two pilot sets): B10 + G3 MAE 2.296 / 2.654 / 2.316
  vs B10 2.316 / 2.552 / 2.345 (TMT worse).
- Exploratory, not pre-registered: B5 + G3 (G3 replacing C9) mean MAE 2.458 vs B5 + C9 linear 2.483,
  B10 2.404 — G3 is a better replacement for C9 than C9 is as a linear term, but the comparison
  with B10 (non-linear C9 use) needs G3 on the training sets.
- Pass agreement 0.77–0.94 (TMT pass 1 diverged).
- Tokens: ≈ 0.2M per pass, 9 passes ≈ 1.8M, plus lessons 0.14M.
