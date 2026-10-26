# FRA check results (2026-10-26 JST)

**Post-hoc data change (user decision, 2026-10-26).** PENDING_FRA pre-registered the full 28-day window (game_time 2026-09-29 to 10-26). Scored instead on the 17Lands Public Game Data file available now (Last Updated 2026-10-17, about 18 days; 297,964 games, sha256 a350666b…), aggregated with `scripts/aggregate_17lands.py` (same script and card definition as the past sets, >= 500 GIH games, 276 cards). Workflow `.github/workflows/fra_score_data.yml`, data in `data/`. Scorer `score_pending.py` (written and selftested before the data was opened), output `score_pending.json`. 271 cards matched (5 basic lands not in the frozen files). Nothing was refit.

| # | Test | Candidate (MAE pp / Spearman) | Baseline | Verdict |
|---|---|---|---|---|
| 1 | C3 LLM features | c3 2.454 / 0.546 | baseline21 2.605 / 0.442 | supported |
| 2 | Case 2 BT | adj_w0.3 2.433 / 0.577 | pred_gih 2.390 / 0.586 | reported only (worse) |
| 3 | Case 2b debiased BT, Rule P-FRA | adj2b_w0.3 2.409 / 0.598 | pred_gih 2.390 / 0.586 | not supported (MAE worse) |
| 4 | Colour hosers | 2 of 5 cards have >= 500 games; adjusted closer on both (MAE 1.13 vs 3.30) | published | reported only |
| 5 | Production forecast | MAE 2.390, Spearman 0.586, 80% range coverage 0.790 | – | reported |
| 6 | C4 | B 2.384 / 0.562 | A 2.390 / 0.586 | not supported (Spearman worse) |
| 7 | C5 | B5 2.415 / 0.553 | B 2.384 / 0.562, A 2.390 / 0.586 | not supported |
| 8 | Colour-pair D_B5 | pred_D_B5 MAE 1.607, Spearman −0.018 | F0_A MAE 1.303, Spearman 0.091 | reported only |
| 9 | AI set reading D10 | pred_AI Spearman −0.224; z-mean −0.273 | pred_D_B5 −0.018, F0_A 0.091 | reported only |
| 10 | C9 (B10), Rule F10 | B10 2.316 / 0.604 | B5 2.415 / 0.553, A 2.390 / 0.586 | supported |

G1 v2 (branch `research/g1-fra-score`, `eval_v2/FRA_SCORE_NOTE.md`, run once): arm0 = B10 MAE 2.316 / 0.604 (matches item 10). pred_v2 MAE −0.013 (CI −0.061 to +0.033), Spearman +0.008, top-10 under-prediction +0.14, top-20 +0.15 → F1 true, F2 false, F3 true, adopt_proposal false. P4 not failed. Unconverted pred_v2_raw (not the pre-registered arm, report only): MAE −0.058, top-20 −0.65 (CI −1.05 to −0.21).

Item 8 pair win rates are non-splash two-colour decks over the same file; 10 pairs only, so the Spearman values are very noisy.

## Additional items (2026-10-26)

Items 11 and 12 scored once with `score_extra.py` (output `score_extra.json`), on the same FRA file as items 1-10 (10/17 update, about 18 days, post-hoc window change, user decision; `data/FRA_gih_28d.csv`, >= 500 GIH games, 276 cards, 271 matched; the 5 basic lands are not in the frozen files). Same name matching as `score_pending.py`; no front-face fallback was needed. Nothing was refitted or retuned; the calculation was run a single time.

**Item 11: B10 spread correction S (Rule F22).** Frozen file `research/g2_bias_spread/fra_frozen_predictions.csv` on `origin/research/g1-grade-diagnosis` (sha256 54a7ed7a... re-checked against the `.json`; pred_B10 identical to the item 10 file). pred_B10S = set mean + b (pred_B10 - set mean), b = 1.1048. Predictions x100 to pp. Following the PLAN, MAE is on set-centred values (actual and prediction each minus their mean over the 271 cards); raw MAE is shown too.

| Arm | MAE centred (pp) | MAE raw (pp) | Spearman | Top 10% by prediction (28 cards): mean(actual - pred), centred | same, raw | Slope of actual on pred |
|---|---|---|---|---|---|---|
| pred_B10 | 2.3163 | 2.3162 | 0.6039 | +1.32 | +1.30 | 1.175 |
| pred_B10S | 2.2937 | 2.2939 | 0.6039 | +0.82 | +0.77 | 1.064 |

S beats B10 on MAE by 0.023 pp (centred; 0.022 raw). Spearman is identical, as constructed. The top-10% under-prediction shrinks from +1.32 to +0.82 pp (indicative, one set). Verdict on FRA per PENDING_FRA item 11 rule ("S beats B10 on MAE (Spearman identical by construction); also report predicted-top-10% mean(actual - pred) (indicative, one set)"): supported. The 28-set Rule F22 conditions (pooled MAE down, Spearman not down by more than 0.0005, 15 or more of 28 sets improved, gain > 0.01 pp) were already judged on 28 sets and cannot be re-evaluated on one set; the FRA gain (0.023 pp) is above the 0.01 pp bar and is within the noise of a single set.

**Item 12: B10 80% prediction range (M5), coverage, report only (no pass/fail).** Frozen file `research/fra_b10_range/fra_b10_range.json` on `origin/research/fra-b10-range` (sha256 aefd4800... re-checked against `fra_b10_range.meta.json`; its predictions_sha256 matches the item 10 file). Range = pred_B10 +- radius. Production comparison: Pages `data/gih-range-fra.json`, range = gih +- radius, gih from `data/adopted-gih-fra.json.gz` (same reading as item 5; coverage 0.790 reproduces item 5). Width = 2 x radius, in pp. Rarity from `research/gih_llm_extract/fra_frozen_predictions.csv` (the other frozen files have none; `land` = the 10 non-basic lands). Target 80%.

| Group | n | B10 coverage | B10 mean width | Production coverage | Production mean width |
|---|---|---|---|---|---|
| All | 271 | 0.801 | 7.05 | 0.790 | 7.48 |
| Common | 71 | 0.789 | 5.63 | 0.831 | 5.82 |
| Uncommon | 105 | 0.810 | 6.86 | 0.810 | 7.13 |
| Rare | 55 | 0.836 | 8.45 | 0.764 | 9.18 |
| Mythic | 30 | 0.800 | 9.43 | 0.700 | 10.46 |
| Land (non-basic) | 10 | 0.600 | 4.29 | 0.700 | 4.69 |

Point-prediction MAE of the two centres: B10 2.316, production 2.390.

**Note on item 12 (not a prior freeze).** The commit that froze this range (5f03ae6, 2026-10-26 09:30 JST) is later than the commit of the FRA actuals on this branch (7956a3a, 09:24 JST), so it cannot be called a prior freeze. The range was built only from the frozen B10 predictions and the 28-set out-of-fold residuals and no FRA outcome was read, but that is a statement of intent, not something the commit order shows. Treat the coverage as reported, not as a pre-registered test.
