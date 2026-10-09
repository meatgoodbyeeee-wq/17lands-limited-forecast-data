# Pending FRA checks (prospective tests frozen before FRA 17Lands data)

Everything here was frozen and committed before any FRA outcome data existed. Score each item only on the **FRA 28-day Public Game Data** (Premier Draft, game_time 2026-09-29 to 2026-10-26, cards with ≥ 500 GIH games, GIH WR in pp, within-set MAE and Spearman). Do not refit or retune anything. Pages changes need an explicit user decision.

Data status: `live/fra-public-game.json`, updated daily by `.github/workflows/fra-public-game-daily.yml`. The data is ready when `status` is not `unavailable` and the observations cover the full window. All 17Lands S3 access goes through GitHub Actions, because the sandbox proxy blocks it. The 17Lands Card Data API must not be used before 2026-10-13 00:00 JST, and is not needed here.

| # | Test | Frozen file | Baseline | Rule (pre-registered) | Details |
|---|---|---|---|---|---|
| 1 | Case 1: C3 LLM features | `research/gih_llm_extract/fra_frozen_predictions.csv` (sha256 in the `.json`) | baseline21 arm | C3 arm beats baseline21 on MAE and Spearman (indicative, one set) | `research/gih_llm_extract/RESULTS.md` |
| 2 | Case 2: blind rankings → Bradley–Terry | `research/case2_pairwise/fra_frozen.csv`, column `adj_w0.3` | `pred_gih` (production `gih-c3-28set-20260929`) | Reference only (Rule P already failed on HOB/MSH) | `research/case2_pairwise/RESULTS.md` |
| 3 | **Case 2b: debiased BT** | same file, column `adj2b_w0.3` | `pred_gih` | **Rule P-FRA: improves both MAE and Spearman → supported** | same |
| 4 | Colour-hoser mixture (5 hosers) | branch `research/hoser-metrics`: `research/hoser_mixture/fra_frozen.csv` (`adjusted` vs `published`) | `published` | Per-card comparison only; Rule H already failed | `research/hoser_mixture/RESULTS.md` on that branch |
| 5 | Production forecast itself | Pages `data/adopted-gih-fra.json.gz` (`gih-c3-28set-20260929`) and range `data/gih-range-fra.json` | – | Report MAE, Spearman, 80% range coverage | Pages repo |
| 6 | **C4 finer card effects (Rule F passed on 28 sets)** | `research/c4_fine_effects/fra_frozen_predictions.csv` (sha256 in the `.json`), columns `pred_B` vs `pred_A` (= production) | `pred_A` | B beats A on MAE and within-set Spearman (indicative, one set) | `research/c4_fine_effects/RESULTS.md` |
| 7 | **C5 atomic effect tags (Rule F5 passed on 28 sets)** | `research/c5_atomic_effects/fra_frozen_predictions.csv` (sha256 in the `.json`), columns `pred_B5` vs `pred_B` and `pred_A` | `pred_B`, `pred_A` | B5 beats B and A on MAE and within-set Spearman (indicative, one set) | `research/c5_atomic_effects/RESULTS.md` |
| 8 | **Colour-pair strength D_B5 (deck model with B5 card predictions; best pair model on 26 sets, Spearman 0.457, reported arm of D9)** | `research/d9_colour_strength/fra_frozen_pairs.csv` (sha256 in `fra_frozen_pairs.json`), column `pred_D_B5` vs `F0_A` (current site formula) | `F0_A` | Reported: within-set Spearman of the 10 pairs and MAE (scale fitted on the 26 sets) against the centred FRA pair win rate. Pair win rates: Premier Draft, 28-day window, non-splash two-colour decks, computed like `scripts/deck_pair_aggregate.py` (that script refuses FRA by design; at verification allow FRA explicitly, after the 28-day window is complete) | `research/d9_colour_strength/RESULTS.md` |
| 9 | **AI reading of the whole FRA set: colour-pair strength (D10)** | `research/d10_fra_set_reading/fra_frozen_ai_pairs.csv` (sha256 in `fra_frozen_ai_pairs.json`), column `pred_AI` (mean of 3 independent readers) | `pred_D_B5`, `F0_A` (item 8) | Reported: within-set Spearman of the 10 pairs vs the centred FRA pair win rate (same data as item 8), for pred_AI, pred_D_B5, F0_A and the mean of within-set z-scores of pred_AI and pred_D_B5 | `research/d10_fra_set_reading/PLAN.md` |
| 10 | **C9 power questions ×3 passes (Rule F10 passed on 28 sets)** | `research/c9_power_questions/fra_frozen_predictions.csv` (sha256 in the `.json`), columns `pred_B10` vs `pred_B5`, `pred_A` | `pred_B5`, `pred_A` | B10 beats B5 and A on MAE and within-set Spearman (indicative, one set; FRA is the clean test because the labellers may remember past cards) | `research/c9_power_questions/RESULTS.md` |

Case 2 sha256 at freeze: `9d1d0e692764f91f353913b775647cceb4db881c389a5e8f19f9cfdfd65d309b`.

After scoring, write `research/fra_check/RESULTS.md`, open a PR, and report to the user in Japanese. Mark each item done here.

C4 freeze note: FRA early 17Lands data (247 cards, 2026-10) was looked at earlier in the project for the early check, before C4 was designed; C4 design, rubric and training did not use it. The freeze is therefore prospective in intent but not blind to the early numbers; the 28-day data decides.
