# N2 results — near-duplicate residual correction: Rule N2 fails (the correction makes the corrected cards worse)

Executed as pre-registered in PLAN.md (commit before computation; definition, thresholds 0.90 primary / 0.95 / 0.80, k = 1, seed 20261026 unchanged). Script `n2.py` (+ `prep.py`, `dist.py`); outputs `summary_by_threshold.csv`, `breakdown.csv`, `corrected_cards_primary.csv`, `result.json`.

## Matches
| threshold | corrected cards | pairs | mean partners/card |
|---|---|---|---|
| 0.95 | 290 | 280 | 1.9 |
| **0.90 (primary)** | **392** | **470** | 2.4 |
| 0.80 | 638 | 1,053 | 3.3 |
(of 7,075 cards; same-name reprints excluded by definition.)

## Rule N2 (primary 0.90) — FAIL
| check | value | result |
|---|---|---|
| 1. MAE on corrected cards, B10 -> corrected | 1.544 -> 1.768 (+0.224) | fail |
| 2. bootstrap 95 % CI of mean paired |err| difference (10,000, seed 20261026) | [+0.144, +0.307] (upper must be < 0) | fail |
| 3. pooled MAE (7,075 cards) | 2.2311 -> 2.2435 | fail |
| 4. mean within-set Spearman | 0.6248 -> 0.6204 (−0.0044) | fail |

Report-only thresholds (also all fail): 0.95: corrected-card MAE 1.418 -> 1.645, CI [+0.142, +0.314], pooled 2.2404, Spearman 0.6217. 0.80: 1.682 -> 1.814, CI [+0.063, +0.201], pooled 2.2430, Spearman 0.6205.
Only 39 % of corrected cards improved at 0.90.

## Why
The partner's residual is not positively related to the target's: correlation between the mean partner residual and the target's own residual is −0.18 (0.90), −0.16 (0.95), +0.01 (0.80). Likely cause (interpretation, not tested): B10 for the target set is trained with the partner's set included, so near-identical text already pulls the target's prediction toward the partner's actual; the partner's remaining OOF residual is then (if anything) the opposite sign. Corrections have SD ~0.9 pp against a corrected-card MAE of only 1.5 pp (these near-duplicate cards are already predicted well), so they add noise. This is the same OOF-leak caveat as G2/N1 (residuals come from models that saw S), and it works against N2 here.

## Breakdown at 0.90 (MAE B10 -> corrected; `breakdown.csv`)
- Rarity: common 331 cards 1.48 -> 1.69; uncommon 25: 1.89 -> 2.34; rare 36: 1.86 -> 2.13 (no mythic matches).
- Category: Creature 150: 1.53 -> 1.66; Land 124: 1.40 -> 1.61; Instant 76: 1.45 -> 1.62; Sorcery 13: 2.71 -> 4.16; Aura 11: 1.74 -> 2.04; Equipment 10: 2.55 -> 2.96; Enchantment 8: 1.59 -> 1.91. Worse in every group.

## Largest effects (0.90)
Gains: DMU Shore Up (partner TLA Octopus Form, cos 1.00) +1.9 pp; STX Biblioplex Assistant / ONE Meldweb Curator (each other, 0.97) +1.9 / +1.5; LCI Sunfire Torch (AFR Spare Dagger 0.93) +1.9; EOE Sacred Foundry (3 ECL tri-lands) +1.6; DFT Pothole Mole / MID Eccentric Farmer (each other) +1.4 / +1.3.
Losses: DMU Pilfer and FDN Pilfer (partner ONE Duress, 0.91) −3.9 each; DMU Vanquisher's Axe (SNC Jackhammer) −3.3; MSH Super Speed (BRO Military Discipline) −3.2; SOS Wild Hypothesis (STX Fractal Summoning) −2.5.

## Reference only (not in judgement): Tricorder (TRK)
With the same definition Tricorder has **0** matching past cards at 0.90, 0.95 and 0.80 -> correction **0.0 pp**. Its nearest eligible card is MSH S.H.I.E.L.D. Spy Kit, but text cosine is only 0.66 (reminder text removed; "attacks alone, untap and scry 1" vs "attacks, surveil 1"), below every threshold. Spy Kit itself also has no match at any threshold, so the motivating example is not covered by this definition (a looser cutoff such as ~0.65 would be needed, which was not pre-registered). No TRK prediction or actual is written.

## Deviations / notes
- Nothing deviated from the plan. R4 uses "new − old > −0.0005".
- Same-name reprints were excluded (not reported separately).
- Nothing adopted or deployed; no FRA/TRK actuals used.
