# C5: atomic effect tags — result (Rule F5, pre-registered): supported

7,010 card texts of the 28 production sets + 290 FRA cards were broken into atomic effects by blind labelling agents (58 tags at level 1/2, scales RATE/CLK/BLK, 3 counts; `RUBRIC.md`). Leave one set out, production model (ET 70% + TF-IDF/Ridge 30%, ×1.25), 28 sets. B5 uses seeds 20260922–24; the reported arms use one seed.

| arm | pooled MAE (pp) | mean within-set Spearman | sets with lower MAE vs B / vs A |
|---|---|---|---|
| A production | 2.392 | 0.562 | – |
| B = A + C4 | 2.353 | 0.578 | – / 25 |
| **B5 = A + C4 + C5** | **2.292** | **0.606** | **24 / 27** |
| A + C5 (no C4), reported | 2.304 | 0.602 | 22 / 25 |
| tags only (no scales/counts), reported | 2.328 | 0.592 | 24 / 26 |
| level-binarised tags, reported | 2.290 | 0.606 | 24 / 26 |

Rule F5 (B5 vs B): MAE lower ✔ (−0.061 pp), Spearman higher ✔ (+0.028), ≥ 15 sets lower MAE ✔ (24/28), gain > 0.01 pp ✔ → supported. B5 vs A: −0.100 pp MAE, +0.044 Spearman, 27/28 sets.

By rarity (MAE, pp), A → B → B5: common 1.812 → 1.791 → 1.769; uncommon 2.368 → 2.349 → 2.282; rare 3.137 → 3.064 → 2.935; mythic 3.407 → 3.270 → 3.239.

Reading
- Finer decomposition keeps helping, and most for rares and uncommons, where card text is most varied.
- C5 alone (without C4) already beats B; C4 adds only about 0.012 pp on top of C5, so the two overlap. The atomic tags carry most of the information.
- Scales and counts matter: tags alone give 2.328, with scales and counts 2.304. Binarising levels changes nothing, so the 1/2 level split is not needed.
- Caveats: the labellers know the historical cards (leakage would favour the in-sample evaluation); FRA is the clean test. 7,365 keys, 290 FRA; FRA data is not used in design or training.

Frozen for FRA: `fra_frozen_predictions.csv` (columns pred_A, pred_B, pred_B5; sha256 in `fra_frozen_predictions.json`); A and B reproduce the C4 freeze to 1e-13 pp. Pages and production unchanged; adoption is the user's decision.
