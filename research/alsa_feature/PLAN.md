# Improvement 2: ALSA predictions as features for card GIH — pre-registered

Research only; Pages unchanged. FIN, MH3, FRA outcomes not used. No new 17Lands API calls: the development ALSA actuals (`dev_alsa_actuals.csv`, fetched earlier by `scripts/fetch_alsa_actuals.py`, FIN absent) are re-materialised from the stored GitHub Actions artifact (`fin-blind-dev-feature-table`, run 35835189360) by `.github/workflows/alsa_actuals_restore.yml`.
Written before any model is fitted.

## Idea
ALSA reflects how drafters value a card and its colour. Pre-release ALSA predictions (the adopted ALSA model) may carry colour-level information that the card GIH model lacks.

## Data
- ALSA actuals exist only for the 21 research sets (MH3 dropped); the 7 newer sets have none, so this test runs on **21 sets**.
- ALSA model: the adopted configuration (`scripts/export_adopted_alsa.py`: HistGradientBoosting, 250 iterations, lr 0.06, l2 2, seed 20260923, features and semantics as there) on `data/features/dev_feature_22.csv.gz`.

## Leakage control (nested)
For each held-out set s: ALSA predictions for s come from a model trained on the other 20 sets; ALSA predictions for each training set t come from a model trained on the 19 sets other than s and t. ALSA actuals of s are never used, and no GIH value enters the ALSA models.

## Features added to the GIH model (production feature set otherwise unchanged)
For each card, with a = predicted ALSA (lower = taken earlier):
- X1: a − set mean of a
- X2: a − mean a of the card's colour group's commons/uncommons (mean over its colours; colourless/lands: 0)
- X3: mean a of the commons/uncommons of the card's colours, minus the set mean of that quantity over the five colours (colour popularity; 0 if colourless)
- X4: rank percentile of a within the card's rarity in the set

## Arms (leave one set out over the 21 sets; production GIH model, one seed 20260922, same training sets)
- **A**: baseline + C3 features.
- **B**: A + X1–X4.
Test: actual GIH of the held-out set.

## Rule L
B is supported if it (1) lowers pooled MAE, (2) raises mean within-set Spearman, and (3) has lower MAE in at least 12 of 21 sets.
Reported, not used for the decision: B with X3 only; B with X1 only; importance of X1–X4; by rarity.

## What follows
If supported: 3-seed refit of the candidate on the 21 sets, FRA predictions frozen next to production before FRA data is used (the ALSA model for FRA is the adopted one). It would also need ALSA actuals for the 7 newer sets (after 2026-10-13 and the terms-of-use check) before any 28-set adoption. Adoption is the user's decision.
