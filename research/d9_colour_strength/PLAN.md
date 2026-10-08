# D9: colour-pair strength from better card predictions and objective profiles, fed back into card GIH — pre-registered (Rules P9, F9)

Research only; Pages and production unchanged. Written before any D9 feature was computed or scored. FIN, MH3, FRA outcomes are not used.

## Why
The user pointed out that the ranking of the 10 colour pairs differs clearly between sets and is tied to card GIH WR. Checked on the 26 sets with pair data (descriptive, after C8): the actual strength of a card's colour(s) correlates 0.25 with B5's residual (strong colours under-predicted), and correcting B5 with the ACTUAL colour strength would lower card MAE from 2.326 to 2.237 pp (oracle, leave one set out). The best earlier pair prediction (M1, Spearman 0.427) carries almost none of this (correlation 0.06, MAE 2.330). The deck-model study found that with actual card GIH a plain colour formula reaches Spearman 0.62, i.e. pair strength is mostly aggregated card strength; the bottleneck was the card predictions, which are now better (B5 vs production A), and the C8 objective profiles allow better colour-level aggregates.

## Stage 1: pair strength (26 sets × 10 pairs, target = centred pair WR in pp, `research/deck_pair/pair_wr.csv`)
Card predictions: B5 out-of-fold (`research/c5_atomic_effects/oof_B5.csv.gz`; leave one set out, so a set's own outcomes are never used for its own predictions). Cards of a pair = mono-coloured cards of either colour + gold cards of exactly the pair; colourless and lands excluded. Weights w = expected copies per 3 packs (booster layout by rarity, as in C7c). All features centred within set.
- F0_B5: mean B5 prediction of the pair's commons and uncommons (the current site formula, with B5 instead of A).
- D_B5: the six deck-model features F1–F6 (`research/deck_model`) recomputed with B5 predictions.
- **P9 (primary): D_B5 + 7 objective aggregates** from the C8 profiles and environment features: P1 Σw·reach_share over removal (quantity × reach), P2 Σw·reach_threat_share, P3 Σw over above-median bodies (stat_rank_mv ≥ 0.5) at MV 2–3, P4 Σw over creatures blockable by < 90% of the set's creatures, P5 Σw·(atk_survive + blk_survive)/2 over creatures, P6 Σw over value cards (draws, makes tokens, or a creature with an ETB effect), P7 Σw·power over creatures with MV ≤ 3.
Model: ridge alpha 3 on standardised features, leave one set out (as Rule D).

**Rule P9** (P9 vs the earlier best): supported if mean within-set Spearman > 0.427 (M1) and > D_B5, MAE < 1.779 (F0 of the production model, scaled), and better Spearman than F0 (production) in ≥ 15 of 26 sets. F0_B5 and D_B5 are reported.

## Stage 2: back into card GIH (26 sets)
For each card, cs = predicted strength of its colour (mono: mean of its 4 pairs; gold two-colour: its pair; colourless or 3+ colours: 0) from the stage-1 primary model P9 (each set's cs comes from a pair model that did not see that set). B9 = B5 + b·cs, with b fitted on the other 25 sets (least squares of B5 residual on cs, leave one set out).

**Rule F9** (B9 vs B5 on the 26 sets): supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 14 of 26 sets, (4) MAE gain > 0.01 pp. Reported: the same correction with F0_B5 and D_B5 as cs, and with the actual colour strength (oracle ceiling, not a forecast).

If F9 is supported: freeze FRA predictions of B9 (FRA pair strength predicted from FRA's B5 frozen predictions and FRA profiles) next to A, B, B5. Adoption is the user's decision.
