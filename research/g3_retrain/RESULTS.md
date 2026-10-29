# G3 retrain results (2026-10-29) — plan: PLAN.md (pre-registered)
28-set LOSO, G3 = single Opus pass per set. Evaluation set = 17 non-lesson sets; lesson sets reported only.
| 17 sets | B5 (no C9) | B10 (C9) | B11g (G3 replaces C9) | B11h (C9 + G3) |
|---|---|---|---|---|
| MAE (pp, set mean) | 2.375 | 2.325 | 2.330 | **2.308** |
| within-set Spearman | 0.607 | 0.622 | 0.622 | **0.631** |
| top-decile MAE | 4.19 | 4.02 | 3.91 | **3.87** |
| sets better than B10 | 2/17 | – | 8/17 | 13/17 |
28 sets: MAE B10 2.237 / B11g 2.238 / B11h 2.219; top-decile 3.73 / 3.69 / 3.62.
Decision rule (B11g MAE <= B10+0.02 and Spearman >= B10-0.005): PASS (equal to B10).
Reading: G3 is a drop-in replacement for C9 (same accuracy, better top-decile by 0.11pp, 3 Opus passes of C9 not needed). It is not a clear improvement over C9 by itself; G3 + C9 together help a little (-0.017pp MAE, +0.009 Spearman, 13/17 sets; B11h was a diagnostic arm, not pre-registered as primary).
