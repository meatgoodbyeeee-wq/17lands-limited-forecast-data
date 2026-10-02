# C4 (finer card-effect features): result — Rule F supported

28 production sets, leave one set out, production model (ET 70% + TF-IDF/Ridge 30%, ×1.25). 7,010 unique card texts + 290 FRA cards extracted blind in 47 batches (`RUBRIC.md`, `check_raw.py`: 0 format errors, 0 missing). Arm A is the production OOF (`research/production_c3/oof_28set.csv.gz`).

## Rule F (3 seeds)
| | pooled MAE (pp) | mean within-set Spearman | sets lower MAE than A |
|---|---|---|---|
| A production (baseline + C3) | 2.392 | 0.562 | – |
| **B: A + C4 (14 numeric fields + 9 role one-hots)** | **2.353** | **0.578** | **25 / 28** |

All four conditions pass: MAE lower, Spearman higher, ≥ 15 sets, gain 0.040 pp > 0.01 pp. By rarity (A → B, pp): common 1.812 → 1.791, uncommon 2.368 → 2.349, rare 3.137 → 3.064, mythic 3.407 → 3.270.

## Reported only (seed 20260922; A at the same seed 2.392 / 0.562)
| arm | pooled MAE | Spearman | sets lower MAE |
|---|---|---|---|
| A + C4 numeric fields only | 2.357 | 0.575 | 26 |
| A + C4 roles only | 2.389 | 0.564 | 18 |
| C4 instead of C3 (baseline + C4) | 2.394 | 0.560 | 16 |

Reading: the gain comes from the 14 numeric fields; the role letters add almost nothing. C4 does not replace C3 (C3 and C4 together are better than either: C4 alone ≈ A without C3's effect, 2.394). Raw single-field correlations with actual GIH (all cards): STACK +0.28, DEAD −0.19, SWG +0.19, TGT +0.14, DMG +0.13, EVA +0.13, SPD +0.13, SCALE +0.13, TURN −0.06, VULN −0.06.

## Caveats
- The extractor (Claude labelling agents) knows these historical cards, so part of the 28-set gain may reflect remembered strength despite blinding (names hidden, no set, no rarity, factual rubric). C3 had the same caveat and held on the new sets. FRA, released after the extractor's training data, is the clean check.
- FRA predictions of A (production, reproduced to 5e-7 pp) and B were frozen in `fra_frozen_predictions.csv` (sha256 in the `.json`) and added to `research/PENDING_FRA.md` (item 6). Early FRA 17Lands numbers had been viewed in this project before C4 was designed; C4 design, rubric and training did not use them. The 28-day data decides.
- Adoption into production is the user's decision. Pages unchanged.
