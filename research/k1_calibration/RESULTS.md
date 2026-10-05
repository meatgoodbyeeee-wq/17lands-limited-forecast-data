# K1: rarity calibration of B5 — result (Rule K, pre-registered): not supported

Nested leave-one-set-out calibration of the B5 out-of-fold predictions (fitted on the other 27 sets, median regression).

| arm | pooled MAE (pp) | mean within-set Spearman | sets lower MAE vs B5 |
|---|---|---|---|
| B5 | 2.2918 | 0.6061 | – |
| **K1 per-rarity intercept + slope** | **2.2924** | **0.6030** | **12 / 28** |
| K0 global intercept + slope, reported | 2.2883 | 0.6061 (unchanged by construction) | 16 |
| KI per-rarity shift only, reported | 2.2963 | 0.6031 | 11 |
| K1 by least squares, reported | 2.2904 | 0.6032 | 13 |

Rule K: MAE lower ❌, Spearman higher ❌, ≥ 15 sets ❌ (12), gain > 0.01 pp ❌ → not supported.

By rarity (MAE pp, B5 → K1; mean bias actual − predicted): common 1.769 → 1.779 (−0.06 → −0.06); uncommon 2.282 → 2.283; rare 2.935 → 2.924 (+0.05 → −0.07); mythic 3.239 → 3.221 (+0.52 → −0.06).

Reading
- The mythic under-prediction is real and K1 removes it (bias +0.52 → −0.06 pp), but it buys only 0.02 pp of mythic MAE: mythic errors are large in both directions, not a shared offset. Over-predicted and under-predicted mythics cancel in the bias but not in the error.
- Per-rarity shifts move whole rarities against each other inside a set, which costs within-set Spearman (0.606 → 0.603) and common-card accuracy.
- Fitted slopes on all 28 sets are 0.98 (common), 1.15 (uncommon), 1.19 (rare), 1.11 (mythic): uncommons and rares are still slightly compressed even after the ×1.25 stretch. The global re-stretch (K0) helps only 0.003 pp.
- Conclusion: the remaining rare/mythic error is about which rare is good, not about a calibration offset. That points to better per-card information for rares and mythics (the "bomb" judgement, step 2 of the plan), not to post-processing. Pages and production unchanged; nothing frozen for FRA.
