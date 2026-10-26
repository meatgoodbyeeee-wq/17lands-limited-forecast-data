# N2c results — Rule N2c fails (the fair check removes about half of the N2b harm, but the correction still does not help)

Executed as pre-registered in PLAN_N2c.md (committed and pushed before any pair fit). Scripts: `n2c_fit.py`, `n2c_chunk.py`, `n2c.py`; outputs `result_n2c.json`, `n2c_cards_primary.csv`, `n2c_fits.csv.gz` (87 both-excluded fits), `n2c_repro.txt`. k = 1, bootstrap 10,000 resamples, seed 20261026. FRA/TRK actuals not read; nothing adopted.

## Reproduction and cost
- B10 refit with only AFR excluded reproduces `oof_B10.csv.gz` exactly (254 cards, max abs diff 2e-16 locally; 3e-16 on the GitHub runner with pinned numpy 2.5.3 / pandas 3.0.5 / scipy 1.18.1 / scikit-learn 1.9.1, Python 3.13).
- One fit (3 seeds) is about 55 s wall on 2 cores; 87 fits would be about 80 min in the sandbox, so they were run in 29 parallel Actions jobs (3 fits each), about 4 min wall in total.

## Matches (same as N2b primary)
127 corrected cards, 101 card pairs, 87 distinct set pairs, mean 1.59 partners per card. For each pair, the partner residual comes from the B10 fit without both sets, centred within the partner's set.

## Rule N2c (primary) — FAIL
| check | value | result |
|---|---|---|
| 1. MAE on corrected cards | 1.498 -> 1.627 (+0.129; N2b +0.240) | fail |
| 2. bootstrap 95% CI of mean paired abs-error difference | [-0.009, +0.269] (upper must be < 0) | fail (CI now covers 0) |
| 3. pooled MAE (7,075) | 2.2311 -> 2.2334 (N2b 2.2354) | fail |
| 4. mean within-set Spearman | 0.6248 -> 0.6243 (-0.00046; limit -0.0005) | pass, by a hair |
Improved cards: 45.7% (N2b 37%). Correction SD 0.87 pp.

## Residual correlation
Mean partner residual vs the card's own residual (corrected cards): **-0.04** (N2b -0.22). So the leak did produce most of the negative sign, but the correlation is not positive either: the partner residual carries no usable information about the card's residual. The partner residual itself barely changed between the two conditions (old vs new, r = 0.975; SD 1.62 vs 1.65 pp), so the difference comes from small shifts on specific cards, not from a different partner signal.

## Per category (MAE B10 -> new)
Creature 1.38 -> 1.50 (44), Instant 1.43 -> 1.46 (59), Enchantment 1.59 -> 1.78 (8), Equipment 3.01 -> 3.83 (6), Sorcery 1.59 -> 2.04 (8), Aura 0.91 -> 0.66 (2). Worse or equal in every category with more than 2 cards; the Instant change is nearly neutral.

## Largest effects
Gains: DMU Shore Up (partner TLA Octopus Form +4.1) +2.05; SNC Daring Escape +1.84; DFT Pothole Mole / MID Eccentric Farmer (each other, +3.1 / +2.9 partner) +1.57 / +1.45; LCI Staggering Size +1.48; MOM Coming In Hot +1.30; MSH Rapid Rescue +1.28; TLA Pillar Launch +1.08.
Losses: DMU Vanquisher's Axe (SNC Jackhammer -6.7) -3.34; BLB Shore Up (same partner as the DMU gain, opposite-sign error) -1.93; VOW Undying Malice -1.65; MOM Kitesail -1.64; KHM Village Rites -1.50; BLB Glidedive Duo -1.39; LCI Ancestors' Aid -1.37; BLB Pond Prophet -1.31.
The same Shore Up pair (DMU +2.05 / BLB -1.93) shows that identical-text cards in different sets can have opposite-sign residuals; the gains and losses largely cancel.

## TRK
Tricorder has 0 definition matches, so its correction is 0 by definition (no TRK values were read).

## Comparison with N2b
Same 127 cards and pairs; only the partner residual differs. Checked: re-computing with the old residual gives N2b's +0.240 (1.738) and -0.22 correlation. N2c: harm +0.129 instead of +0.240, CI no longer clearly above zero, correlation -0.04 instead of -0.22, pooled MAE and Spearman essentially unchanged. The leak hypothesis explains why N2b looked actively harmful, but not a benefit: under the production condition the correction is neutral-to-slightly-negative and fails Rule N2c.

## Limits / notes
- Same as plan: small sample (127 cards), definition fixed from human review of past sets, bootstrap resamples cards not pairs (so the CI is, if anything, too narrow), both-excluded models use 26 sets instead of 27 (slightly noisier partner residual).
- Rule N2c condition 4 passes with a margin of 0.00004; not meaningful.
- No deviations from the plan. The Actions workflow `n2c_pairs.yml` was removed after collecting the fits (artifacts could not be downloaded through the sandbox proxy, so the workflow committed one combined file instead).
