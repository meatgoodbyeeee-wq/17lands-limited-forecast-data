# C7c: rarity-weighted set support for strong synergy pairs — result (Rule F7c, pre-registered): not supported

The support a card receives from the set was recomputed as the expected number of partner copies a drafter sees (each card weighted by the booster layout of its rarity in its set; play-booster layout for sets with ≥ 95 uncommons, otherwise draft-booster layout; `layouts.json`), next to the plain number of partner cards. Table: the 18 strong pairs. 6 features. 28 sets, leave one set out, production model, B7c with seeds 20260922–24.

| arm | pooled MAE (pp) | mean within-set Spearman | sets lower MAE vs B5 |
|---|---|---|---|
| B5 (A + C4 + C5) | 2.2918 | 0.6061 | – |
| B7b (C7b: shares, unweighted) | 2.2921 | 0.6060 | 12 |
| **B7c = B5 + 6 columns** | **2.2923** | **0.6058** | **11 / 28** |
| counts only (4), reported | 2.2934 | 0.6055 | 10 |
| rarity-weighted only (4), reported | 2.2916 | 0.6057 | 15 |
| shuffled-label control, reported | 2.2940 | 0.6064 | 9 |

Rule F7c (B7c vs B5): MAE lower ❌ (+0.0005 pp), Spearman higher ❌, ≥ 15 sets ❌ (11), gain > 0.01 pp ❌ → not supported. The rarity-weighted version alone is the best of the reported arms (2.2916, 15/28 sets) but its gain over B5 is 0.0002 pp, which is noise. The plain count and the weighted count are almost the same feature (correlation 0.97 across cards).

Reading: counting partners by how often a drafter meets them does not change the picture. Across C7, C7b and C7c, tag synergy (within the card and from the set) adds nothing to B5 for card GIH WR. Not tested: pair effects learned from data; deck-level synergy; synergy with the drafter's own colour choices. Pages and production unchanged; B5 stays the best card model; nothing frozen for FRA.
