# D9: colour-pair strength and its feedback into card GIH — results: Rule P9 not supported, Rule F9 not supported

26 sets × 10 pairs (stage 1) and the cards of those 26 sets (stage 2), leave one set out throughout.

## Stage 1: pair strength

| arm | mean within-set Spearman | MAE of centred pair WR (pp) | sets better than F0 (production) |
|---|---|---|---|
| F0 with production card predictions (current site formula) | 0.350 | 1.779 | – |
| M1 (best earlier ensemble) | 0.427 | 1.741 | 14 |
| F0 with B5 card predictions, reported | 0.376 | 1.769 | 14 |
| **D_B5: deck model F1–F6 with B5 card predictions, reported** | **0.457** | **1.711** | **18** |
| **P9 (primary) = D_B5 + 7 objective aggregates** | **0.404** | **1.755** | **14** |
| objective aggregates alone, reported | 0.174 | 1.934 | 8 |

Rule P9: Spearman > 0.427 ❌ (0.404), > D_B5 ❌, MAE < 1.779 ✔, ≥ 15 sets ❌ → not supported. Single objective aggregates are weak (Spearman 0.02–0.16: removal reach 0.02, threat reach 0.10, good 2–3-drop bodies 0.15, combat 0.16, cheap power 0.16); added to D_B5 they cost accuracy.

The reported D_B5 is the best pair prediction so far (0.457, 18/26 sets, MAE 1.711): better card predictions (B5) carry over to colour strength. It was a reported arm, not the candidate; a decision on it would need its own confirmation (FRA or a fresh rule).

## Stage 2: predicted colour strength back into card GIH (B9 = B5 + b · colour strength)

| colour strength used | card MAE (pp) | Spearman | sets lower MAE (of 26) |
|---|---|---|---|
| none (B5) | 2.2909 | 0.6068 | – |
| **P9 (primary)** | **2.2900** | **0.6064** | **12** |
| D_B5, reported | 2.2876 | 0.6082 | 13 |
| F0_B5, reported | 2.2912 | 0.6074 | 14 |
| actual colour strength (oracle ceiling) | 2.2114 | 0.6382 | 22 |

Rule F9: MAE lower ✔ (−0.0009 pp), Spearman higher ❌, ≥ 14 sets ❌ (12), gain > 0.01 pp ❌ → not supported.

## Why predicted colour strength does not help the cards
Correlation with B5's card residual: actual colour strength 0.234; predicted (P9 0.063, D_B5 0.072, F0_B5 0.056). The part of the actual colour strength that the B5-based pair prediction does NOT explain still correlates 0.227 with the card residual. In other words, the colour effect B5 misses is exactly the part of colour strength that is not an aggregate of card quality. Any pair prediction built from card predictions or card profiles cannot recover it; it needs information outside the individual cards (how the format actually plays: speed, which archetypes work, how drafters move).

Pages and production unchanged; nothing frozen for FRA.
