# K1: rarity calibration of B5 predictions — pre-registered (Rule K)

Research only; Pages and production unchanged. Written before any calibration was fitted or scored. FIN, MH3, FRA outcomes are not used. No new AI extraction (no leakage risk from the extractor's knowledge of past cards beyond what B5 already has).

## Why
Error breakdown of B5 (28-set out-of-fold predictions): mythic rares are predicted 0.52 pp too low on average and rare/mythic errors are the largest (sd 3.8–4.1 pp vs 2.3 for commons). Tree ensembles pull extreme cards towards the mean; production stretches all predictions by ×1.25 around the training mean, one factor for all rarities. K1 tests whether a per-rarity correction fixes this.

## Method
Input: B5 out-of-fold predictions (`../c5_atomic_effects/oof_B5.csv.gz`, 3 seeds). For each held-out set s, a calibration is fitted on the out-of-fold predictions and actual GIH WR of the other 27 sets and applied to set s (nested leave one set out). Fitting is by least absolute deviation (median regression, the loss matches MAE). Note: the other sets' out-of-fold predictions came from models that included set s in training; with 2–8 calibration parameters this leak is negligible, and it is the standard way to calibrate stacked predictions.

- **K1 (primary): per-rarity intercept and slope** (4 rarities × 2 = 8 parameters): y = a_r + b_r · p.
- Reported only: K0 global intercept and slope (2 parameters, a re-stretch; cannot change within-set Spearman); KI per-rarity intercept only (shift, slope 1); K1-OLS (K1 fitted by least squares).

## Rule K (K1 vs B5)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp. If supported: compute FRA calibrated predictions from the frozen B5 FRA predictions (`../c5_atomic_effects/fra_frozen_predictions.csv`, pred_B5) with K1 fitted on all 28 sets, freeze them next to A, B, B5, and add the check to PENDING_FRA. Adoption is the user's decision.
