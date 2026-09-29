# GIH WR forecast range ("予測の幅") by card group

Research only until the user adopts it. Point predictions are unchanged. FIN and MH3 are not used.

## Problem
The site shows one fixed range for every card: ±3.684pp, inherited from the legacy Ridge model (`model.json` `interval_radius`), not from the adopted ET+TF-IDF ensemble.
On the adopted model's 21-set out-of-fold residuals (`research/gih_21set/baseline/baseline_oof.csv.gz`), that range covers 77.7% of cards overall but 88.5% of commons and only 59.9% of mythics (exploratory check made before this plan).
The "outside the range" flag on the site therefore fires mostly on rares and mythics.

## Target
A nominal **80%** range (keeps the current overall meaning of the band).

## Data
- Residual r = actual − pred (pp) from the 21-set baseline OOF (adopted model config, seed 20260922). 5,344 cards.
- Card features from `data/features/dev_feature_22.csv.gz` (pre-release only).
- Type groups: creature (type line has Creature); spell (Instant/Sorcery, not creature); other noncreature nonland permanent (artifact, enchantment, planeswalker, battle); land.

## Evaluation
Leave-one-set-out over the 21 sets: range parameters are fitted on the other 20 sets' residuals only, then scored on the held-out set.
(The other sets' OOF residuals come from models that saw the held-out set's labels; this second-order effect is accepted, as in standard cross-conformal practice.)

Metrics: pooled coverage; coverage by rarity and by type group; per-set coverage spread; mean width; mean interval score (Winkler, α = 0.2: width + (2/α)·distance outside).

## Candidates (fixed before running; no tuning on results)
- M0 current: ±3.684 for every card
- M1 global: symmetric, 80% quantile of |r|
- M2 rarity: symmetric, 80% quantile of |r| per rarity
- M3 rarity asymmetric: 10% and 90% quantiles of signed r per rarity
- M4 rarity × type: symmetric, 80% quantile of |r| per cell, shrunk toward the rarity quantile with pseudo-count 50: q = (n·q_cell + 50·q_rarity)/(n + 50)
- M5 normalized conformal: ExtraTrees (300 trees, leaf 20, max_features 0.6) predicts |r| from the pre-release features + pred; calibration scores |r|/σ̂ use 5-fold set-grouped cross-fitting within the 20 training sets; range = pred ± q80·σ̂ (σ̂ floored at 0.5pp)

## Pre-registered decision rule
1. Pooled LOSO coverage within 0.78–0.82.
2. Every rarity group within ±0.05 of 0.80.
3. Every type group within ±0.07 of 0.80.
4. Among candidates passing 1–3, the lowest mean interval score wins. A more complex candidate (order M1 < M2 < M3 < M4 < M5) beats a simpler passing one only if its interval score is at least 1% lower.
5. If none passes 1–3, apply rule 4 to candidates passing 1–2.

Adoption into the site is a separate, explicit decision by the user.
