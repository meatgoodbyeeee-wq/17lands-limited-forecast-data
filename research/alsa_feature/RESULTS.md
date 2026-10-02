# Improvement 2: ALSA predictions as GIH features — result (Rule L, pre-registered in PLAN.md)

**Not supported.** 21 research sets, leave-one-set-out, one seed (20260922), nested ALSA predictions (no leakage of the held-out set's ALSA actuals or any GIH value into the ALSA models).

| Arm | Pooled MAE (pp) | Mean within-set Spearman | Sets with lower MAE than A |
|---|---|---|---|
| A: baseline + C3 | 2.392 | 0.567 | – |
| B: A + X1–X4 | 2.385 | 0.573 | **11 / 21** (need ≥ 12) |
| (reported) X3 only | 2.390 | 0.568 | 15 / 21 |
| (reported) X1 only | 2.374 | 0.576 | 13 / 21 |

Rule L: MAE lower ✔, Spearman higher ✔, sets ≥ 12 ✘ → fails. The gains are tiny (MAE −0.008 pp, Spearman +0.005) and inconsistent across sets (11/21 lower MAE, 11/21 higher Spearman). By rarity (A → B, pp): common 1.828 → 1.820, uncommon 2.403 → 2.421, rare 3.081 → 3.049, mythic 3.483 → 3.434.

The colour-popularity feature X3, the one aimed at deck colour information, does almost nothing (MAE −0.002 pp). X1 (ALSA relative to the set) alone is the best arm but was not the pre-registered candidate, so it is exploratory only (MAE −0.019 pp, Spearman +0.009, 13/21) and does not reopen the decision.

Notes: ALSA actuals exist for 21 sets only (KHM snow-land duplicates dropped, first row kept); 2.3% or fewer of cards per set lacked an ALSA row and received the set-mean ALSA. Pages and production unchanged. No FRA data used.

Conclusion: pre-release ALSA predictions add no usable information beyond the existing card features. They are predicted from those same features, so this was the expected ceiling. No FRA freeze, no adoption step.
