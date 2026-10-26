# N2b results — Rule N2b fails (restricting to human-confirmed near-duplicates still makes the corrected cards worse)

Executed as pre-registered in PLAN_N2b.md (committed and pushed before computation). Script `n2b.py` (+ `prep.py`); outputs `result_n2b.json`, `n2b_cards_<arm>.csv`. k = 1, bootstrap 10,000 resamples, seed 20261026. FRA/TRK actuals not read; nothing adopted.

## Matches
| arm | corrected cards | pairs | by category (cards) |
|---|---|---|---|
| **primary** (creature: cos>=0.95, same mv, same P/T; non-creature: cos>=0.95) | **127** | **101** | Instant 59, Creature 44, Enchantment 8, Sorcery 8, Equipment 6, Aura 2 |
| (a) non-creature cos>=0.90 | 162 | 121 | Instant 76, Creature 44, Sorcery 13, Aura 11, Equipment 10, Enchantment 8 |
| (b) lands only, cos>=0.80 | 137 | 613 | Land 137 (mean 8.9 partners) |
Primary pairs by category: Instant 41, Creature 39, Enchantment 13, Sorcery 4, Equipment 3, Aura 1.
Estimated share truly "nearly the same" (review sample, primary definition): 10/10 S (Wilson 95% lower ~72%); in-sample for the non-creature part, so optimistic.

## Rule N2b (primary) — FAIL (all four conditions)
| check | value | result |
|---|---|---|
| 1. MAE on corrected cards | 1.498 -> 1.738 (+0.240) | fail |
| 2. bootstrap 95% CI of mean paired |err| diff | [+0.105, +0.375] (upper must be < 0) | fail |
| 3. pooled MAE (7,075) | 2.2311 -> 2.2354 | fail |
| 4. mean within-set Spearman | 0.6248 -> 0.6236 (-0.0012) | fail |
Improved cards: 37%. Correction SD 0.85 pp.

## Report-only arms (both also fail all four)
- (a) nc 0.90: corrected MAE 1.626 -> 1.931, CI [+0.159, +0.456], pooled 2.2380, Spearman 0.6225, improved 38%.
- (b) lands 0.80: corrected MAE 1.356 -> 1.487, CI [+0.046, +0.217], pooled 2.2336, Spearman 0.6237, improved 39%.

## Residual correlation (mean partner residual vs target's own residual, corrected cards)
primary -0.22 (N2: -0.18); arm (a) -0.29; arm (b) lands -0.18. Negative, so the correction pushes the wrong way, as in N2. Per category in primary (MAE B10 -> new): Creature 1.38 -> 1.56 (44), Instant 1.43 -> 1.59 (59), Enchantment 1.59 -> 1.91, Equipment 3.01 -> 4.02, Sorcery 1.59 -> 2.20, Aura 0.91 -> 0.69 (2 cards). Worse in every category with >2 cards.

## Largest effects (primary)
Gains: DMU Shore Up (partner TLA Octopus Form +3.9 pp) +1.9; SNC Daring Escape (MOM Coming In Hot, WOE Kindled Heroism) +1.4; DFT Pothole Mole / MID Eccentric Farmer (each other) +1.4 / +1.3; MOM Coming In Hot +1.2; LCI Staggering Size +1.1.
Losses: DMU Vanquisher's Axe (SNC Jackhammer, -6.7) -3.3; BLB Shore Up (same partner as the DMU gain; the DMU/BLB copies have opposite-sign errors) -1.9; MOM Kitesail -1.8; STX Sudden Breakthrough -1.7; VOW Undying Malice -1.7; LCI Ancestors' Aid -1.7.
Arm (a) extra losses: DMU/FDN Pilfer (ONE Duress, cos 0.91) -3.9 each; MSH Super Speed -3.2. Arm (b): EOE Sacred Foundry gains +1.6 (3 ECL tri-lands) but its 4 sibling EOE duals (Breeding Pool, Watery Grave, ...) each lose -1.6 with the same partners, i.e. the correction is shared by cards whose own residuals differ.

## Interpretation (not tested)
Even pairs a human calls "nearly the same" do not share residuals: near-identical text already pulls B10's prediction for the target toward the partner's actual (the partner's set is in the training data), leaving the partner's residual uninformative or opposite. The human review fixed pair quality, but the failure in N2 was not pair quality.

## Deviations / notes
- Non-creature pairs keep N2's |mv diff| <= 1 (the instruction listed four conditions to keep; this was my reading and is stated in the plan). Creatures need equal mv. Lands (arm b) also keep +-1.
- In result_n2b.json, R4 shows 0.0 for false (numpy bool through float); values in the table above are correct.
- Known limitations as in plan (OOF leak, 81-pair sample, same-set bootstrap resampling by card).
