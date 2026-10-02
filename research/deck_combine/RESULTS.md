# Deck colour: combining the rejected ideas — result (Rule M, pre-registered): not supported

26 sets × 10 pairs, leave one set out. All members are LOSO predictions; ensembles average them in pp.

| | mean within-set Spearman | MAE of centred pair WR (pp) | sets better than F0 |
|---|---|---|---|
| F0 current formula | 0.350 | 1.779 | – |
| S draft simulation | 0.134 | 1.919 | 7 |
| D (F1–F6) | 0.416 | 1.790 | 13 |
| A (F1–F6 + official archetype labels) | 0.402 | 1.768 | 10 |
| **M1 mean of F0, D, A, S** | **0.427** | **1.741** | **14** |
| M2 mean of D, A, S | 0.417 | 1.756 | 12 |
| M3 ridge F1–F6+A1–A5+S, alpha 10 | 0.372 | 1.807 | 11 |
| M4 same, alpha 30 | 0.375 | 1.788 | 11 |

Rule M needs Spearman ≥ max(D, A) + 0.02 = 0.436 and ≥ F0 + 0.05, better than F0 in ≥ 15 sets, MAE below F0. M1 comes closest (Spearman 0.427, 14/26 sets, MAE −0.04pp) but misses the Spearman and set-count thresholds → **not supported**. Putting everything into one ridge (M3/M4) is worse than the parts: with 260 rows the extra features add noise.

Reading: averaging different views gives a small, consistent-looking gain in error (1.779 → 1.741pp) and a modest gain in order (0.35 → 0.43), but the order is still weak (a perfect ranking would be 1.0, and the plain formula on actual card GIH reaches 0.62). The ideas overlap because they all derive from the same card information. Nothing frozen for FRA; Pages unchanged.
