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
