# X1 results (2026-10-26): PASS (primary arm)

MTGAZone pre-release set-review grades (0–5) combined with B10; coefficients for each set fitted on
the other past grade sets only (13 past sets: BLB DFT DSK ECL EOE FDN LCI MKM OTJ SOS TDM TLA TMT).
Primary arm: grades from sections published after the set's 17Lands window start are dropped.

| | pooled MAE (pp) | mean within-set Spearman | sets improved |
|---|---|---|---|
| B10 | 2.160 | 0.616 | – |
| **X1 primary** | **2.082 (−0.079)** | **0.645 (+0.029)** | **13 / 13** |
| X1 all grades (reported; some sections post-release) | 2.008 (−0.153) | 0.678 (+0.061) | 13 / 13 |

Rule: MAE −0.079 ≥ 0.05 ✔, Spearman higher ✔, 13/13 ≥ 9 ✔ → PASS.

By rarity (B10 → X1 primary): C 1.574→1.537, U 2.180→2.110, R 2.753→2.634, M 3.119→2.913.
Top-10% under-prediction: 3.32 → 2.78 pp (all-grades arm 2.36).

FRA, out of sample (coefficients from the 13 past sets; grades published 9/20–21, before release):
MAE 2.316 → 2.122 (−0.194), Spearman 0.604 → 0.663.

Fitted model (stable across folds): ŷ = 0.05 + 0.68·B10Δ + 1.65·(grade − set mean grade) on graded
cards (≈ +1.65 pp per grade point); ungraded cards keep B10.
Spearman(grade, B10 residual) per set: 0.05 (SOS) – 0.48 (LCI), positive in all 14 sets.

Caveats: one source (two reviewers: J2SJosh, Icky); grades transcribed via WebFetch summaries
(spot-checked, not card-by-card); SOS multicolour and TDM green partly missing; FRA grades already
looked at before this plan (signal check), so FRA is confirmation only. Compared with B10, not B10S.
