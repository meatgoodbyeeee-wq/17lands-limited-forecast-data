# N2c — fair check of the N2b correction (pre-registered, written before any pair model was fitted)

Follow-up to N2b (PLAN_N2b.md / RESULTS_N2b.md: Rule N2b failed). Research only; no production model, Pages or TRK file is changed. FRA and TRK actuals are not read. Same branch, never merged.

## Why N2c
In N2b, the correction for card A (set S) used the residual of its partner B (set T) taken from `oof_B10`, i.e. from the model that excludes only T. That model was trained WITH A (set S). In production (predicting a new set) A is not in training, so this information does not exist there. It plausibly explains the negative A-B residual correlation (-0.22). N2c recomputes B's residual under the production condition.

## Definition (identical to N2b primary except the partner residual)
- Pairs (A in S, B in T): same as N2b primary, unchanged: lands excluded; creature: cos >= 0.95 AND equal mana value AND equal P/T; other non-land: cos >= 0.95 AND |mv diff| <= 1; same category, different set, different name, both >= 6 tokens. Same TF-IDF. (127 cards, 101 card pairs, 87 distinct unordered set pairs; list in `n2c_pairs.json`, derived from the definition only, no residuals.)
- A's own prediction: `oof_B10` (only S excluded), unchanged.
- Partner residual r_B: for each needed set pair {S,T}, fit B10 (same code path as `c9.py arm B10`: 3 seeds, same blend, same features) on all sets EXCEPT S and T, and predict both S and T. r = actual_gih*100 - pred*100, then centred by subtracting the mean of r over all cards of that set (for T: all T cards predicted by the both-excluded model; for S, symmetrically, because B's correction uses A's residual). A's correction uses r_B from the {S,T_B} model; with several partners the mean is over partners, each from its own model.
- Correction: corrected_pred_A = pred_A + n/(n+1) * mean_{B in M(A)} r_B (k = 1, n = number of partners).

## Rule N2c (same four conditions as N2b)
(1) MAE of corrected cards lower than B10; (2) paired |err| difference over corrected cards, bootstrap over cards, 10,000 resamples, seed 20261026, 95 % percentile CI upper < 0; (3) pooled MAE over 7,075 cards not worse; (4) mean within-set Spearman (28 sets) not lower by 0.0005 or more. Pass = "worth a follow-up" only. No other thresholds, arms or parameters will be tried.

## Reporting
Number of corrected cards/pairs; Rule N2c numbers; corr(mean partner residual, own residual) over corrected cards (N2b -0.22); comparison with N2b; top gain/loss pairs. Also reported: Tricorder (TRK) has 0 definition matches, so its correction is 0 (stated by definition, TRK values not read).

## Reproduction check (done before this plan, no residuals computed)
`n2c_fit.py` with S only excluded (AFR) reproduces `oof_B10.csv.gz` for AFR exactly (254 cards, max abs diff 2e-16). One fit takes about 55 s wall on 2 cores (87 fits ~ 80 min sequentially); run in parallel via GitHub Actions (`.github/workflows/n2c_pairs.yml`, push to this branch only).

## Known limitations
- The judged sample is small (127 cards, 101 pairs); the creature part rests on 2 human-confirmed S pairs.
- The definition was fixed by human review of past sets, not out-of-sample; N2c reuses it unchanged.
- Bootstrap resamples cards, not pairs (a pair uses each other's residuals), so intervals may be optimistic.
- A's own prediction (oof_B10, S only excluded) is not affected by T, but the both-excluded model has less training data (26 vs 27 sets), so r_B is slightly noisier than a production residual from a full model.
- Pairs whose partner is from the same set as another partner share fits; cards in one set are not independent.
