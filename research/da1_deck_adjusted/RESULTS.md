# DA1 results (plan: PLAN.md, committed and pushed before any computation)

Rule DA1 **fails** (4 of 4 conditions fail). Deck adjustment explains part of the Shore Up gap, but training on it makes B10 worse.

## Checks
- Raw GIH from the new aggregation equals `actual_gih` of `oof_B10.csv.gz` for 27 of 28 sets (max abs diff 5e-17) and games/wins equal `data/compact_28d` for all 21 sets that have a file there (ECL, EOE, HOB, MSH, SOS, TLA, TMT have none; their values equal oof_B10 as above). **HOB differs** (max 0.9 pp, 284,304 vs 241,727 games in the window): the HOB window was still open when the stored aggregate was made. HOB's raw and adjusted values below come from the new snapshot, while Part B scores HOB against the stored `actual_gih` as B10 does.
- 748 cards with >= 500 GIH games in the aggregation are not in the 7,075-card training pool (not used).
- B10 reproduction: the B10 code path gives exactly `oof_B10` for HOB (max abs diff 2e-16); my replica of the fit function (with target replaced) gives the same (2e-16) with the raw target.
- N2b pairs regenerated with the N2b code: 101 pairs, 127 cards, same card set as `n2b_cards_primary.csv`.

## A. Explanation (no pass/fail)
Shore Up and Octopus Form (pp; "set-centred" = minus the mean over the cards of the set):

| card | games | raw GIH | deck-adj | player-adj | colour-adj | raw c. | deck c. | player c. | colour c. |
|---|---|---|---|---|---|---|---|---|---|
| DMU Shore Up | 72,711 | 57.44 | +1.01 | +1.58 | +1.03 | +0.92 | +0.29 | +0.25 | +0.91 |
| BLB Shore Up | 43,241 | 53.69 | +1.45 | +0.46 | +0.56 | -1.90 | -0.05 | -1.65 | -0.70 |
| TLA Octopus Form | 49,596 | 58.17 | +1.33 | +2.96 | +1.95 | +1.98 | +0.39 | +0.81 | +1.57 |

Absolute differences of set-centred values between the cards (pp):

| pair | raw | deck | player | colour |
|---|---|---|---|---|
| DMU Shore Up vs BLB Shore Up | 2.81 | 0.34 | 1.90 | 1.61 |
| DMU Shore Up vs TLA Octopus Form (N2b pair) | 1.06 | 0.10 | 0.56 | 0.66 |
| BLB Shore Up vs TLA Octopus Form (N2b pair) | 3.88 | 0.44 | 2.46 | 2.27 |

Mean absolute difference over the 101 N2b primary pairs (pp; the player and colour columns use the pairs where both cards have the value: 74 and 85 pairs):

| | raw | deck | player | colour |
|---|---|---|---|---|
| mean abs pair diff | 1.745 | 0.738 | 1.181 | 1.387 |
| within-set SD of the value over all 7,075 cards | 3.83 | 1.94 | 3.06 | 3.64 |
| pair diff / SD | 0.456 | 0.381 | 0.387 | 0.381 |
| same-category random cross-set pair diff (200 draws per pair) | 3.48 | 1.59 | 2.59 | 3.25 |
| pair diff / random | 0.50 | 0.46 | 0.46 | 0.43 |

The raw drop 1.745 -> 0.738 is mostly scale: the deck-adjusted value is about half as spread (leave-one-out baseline removes the part of the card's effect carried by the deck, and the slope of raw on deck-adjusted is 1.68). After dividing by the SD or by the random-pair difference, deck adjustment improves pair agreement only a little (0.456 -> 0.381, or 0.50 -> 0.46); player and colour adjustment give about the same. Deck-adjusted differences are smaller than raw in 77 of 101 pairs.

Between-set variance of all cards (pp^2, cards equally weighted, 28 sets): raw between 0.547, within 14.65, between share 3.6 % (SD of set means 0.74 pp); deck-adjusted between 0.097, within 3.76, share 2.5 % (SD of set means 0.31 pp). In relative terms the set-level component shrinks a little more than the within-set part.

Correlation of set-centred values with raw: deck 0.85, colour 0.96, player 0.98 (so the deck baseline removes the most).

## B. Prediction (Rule DA1), 28-set LOSO, scored on raw `actual_gih`

| | pooled MAE (pp) | mean within-set Spearman | sets with lower MAE than B10 |
|---|---|---|---|
| B10 | 2.2311 | 0.6248 | - |
| DA1 (deck-adjusted target) | 2.4059 | 0.5485 | 3 |
| ens (B10 + DA1)/2, report only | 2.2856 | 0.6048 | 6 |
| DA1, in-sample slope variant, report only | 2.4219 | 0.5485 | 3 |

Rule DA1: (1) MAE lower: no (+0.175 pp worse). (2) Spearman not lower by >= 0.0005: no (-0.076). (3) >= 15 of 28 sets lower: no (3). (4) gain > 0.01 pp: no (-0.175). **Fail.** The ensemble is also worse than B10 (MAE +0.055 pp, Spearman -0.020).

Conversion slope b (raw centred on deck-adjusted centred, training sets): 1.68 in every fold (1.67-1.69); in-sample variant 1.99. The set mean is B10's by construction, so the entire difference is within-set.

DA1's prediction is a better predictor of the deck-adjusted outcome itself (mean within-set Spearman vs deck-adjusted actual 0.653 vs B10's 0.609), but against raw GIH it ranks worse (0.548). The correlation of the within-set parts of B10 and DA1 predictions is 0.90.

MAE by rarity (pp), B10 / DA1 / ensemble:
| rarity | n | B10 | DA1 | ens |
|---|---|---|---|---|
| 0 common | 2,723 | 1.743 | 1.919 | 1.790 |
| 1 uncommon | 2,333 | 2.242 | 2.433 | 2.312 |
| 2 rare | 1,532 | 2.822 | 3.004 | 2.887 |
| 3 mythic | 487 | 3.045 | 3.118 | 3.036 |

Top 10 under-predictions of B10 (actual - B10, pp) with DA1: LTR Orcish Bowmasters +12.2 (DA1 +12.9), LCI Zoetic Glyph +12.1 (+10.5), MSH Avengers Assemble! +11.8 (+10.1), SOS Ark of Hunger +11.6 (+10.5), SOS Together as One +11.4 (+10.5), LTR Witch-king of Angmar +10.3 (+8.3), ECL Chronicle of Victory +10.3 (+8.4), ECL Gloom Ripper +10.1 (+9.6), VOW Necroduality +10.0 (+6.1), TMT April O'Neil, Hacktivist +10.0 (+7.8). Mean absolute error on these ten: B10 10.97, DA1 9.46 (selected on B10's error, so partly regression to the mean). Their deck-adjusted actuals are +3.0 to +7.1 pp above the set mean, so the large raw misses are mostly real card effect, not deck.

## Interpretation
- Deck/player information accounts for a part of the Shore Up gap (between the two Shore Ups the raw difference 2.8 pp becomes 0.3 pp deck-adjusted; the player-adjusted difference is 1.9 pp), but the adjusted value is much less spread, and it is not a better target for predicting what the card does to raw GIH: the model trained on it loses rank information and MAE.
- Nothing is adopted. Production, Pages and TRK files unchanged; FRA and TRK data were not read.

## Limitations (in addition to PLAN.md)
- The deck baseline contains the card's own effect through the other games of the same deck, so deck-adjusted values are shrunk (slope 1.68); no attempt was made to un-shrink other than the linear conversion.
- HOB snapshot mismatch (above). Player-adjusted is blank for AFR, KHM, MID, STX, VOW; colour-adjusted is blank for KHM and STX (columns absent).
- No bootstrap/CI was computed for Part A (explanation only).

Files: `da1_a.py`, `da1_b.py`, `da1_eval.py`, `n2_prep.py` (unchanged copy of N2's prep), `repro.py`, `result_A.json`, `result_B.json`, `oof_DA1_raw.csv.gz`, `da1_folds.json`, `pairs_A.csv`, `data/da1_cards.csv.gz`, `data/da1_manifests.json`; aggregation `scripts/da1_aggregate.py` (workflow deleted after use).
