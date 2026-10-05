# C7b: strong synergy pairs only — result (Rule F7b, pre-registered): not supported

Only the 18 pairs at weight +2 of the C7 table were kept (83 pairs at +1 and 7 at −1 removed, on the user's request after questioning some weaker pairs). 4 features: W, Wlvl (within the card), sup_set, sup_col (support from the set). 5.4% of cards carry at least one of the 18 pairs. 28 sets, leave one set out, production model, B7b with seeds 20260922–24.

| arm | pooled MAE (pp) | mean within-set Spearman | sets lower MAE vs B5 |
|---|---|---|---|
| B5 (A + C4 + C5) | 2.2918 | 0.6061 | – |
| B7 (all 108 pairs, C7) | 2.2914 | 0.6067 | 14 |
| **B7b = B5 + 4 strong-pair columns** | **2.2921** | **0.6060** | **12 / 28** |
| within-card only (2), reported | 2.2943 | 0.6052 | 9 |
| set-context only (2), reported | 2.2932 | 0.6052 | 10 |
| shuffled-label control, reported | 2.2928 | 0.6054 | 16 |

Rule F7b (B7b vs B5): MAE lower ❌ (+0.0003 pp, slightly worse), Spearman higher ❌, ≥ 15 sets ❌ (12), gain > 0.01 pp ❌ → not supported. The shuffled control also does not help (it is as flat as B7b).

Reading: with the weaker pairs removed there is still no gain. The strong pairs touch few cards (5%), and the model already uses the same tags directly; a hand-made table of combinations adds nothing it cannot find itself. Hand-written tag synergy is closed for card GIH WR in this form (C7, C7b). Not tested: pair effects learned from data with strong shrinkage; deck-level synergy. Pages and production unchanged; B5 stays the best card model; nothing frozen for FRA.
