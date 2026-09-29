# Case 6: newer training sets, a post-cutoff test of C3, and a top-player GIH target

Research only. FIN (final holdout), MH3 (excluded) and FRA (live; prospective checks only) are not used. Pages is unchanged.
This plan is committed before any new-set or top-player outcome is aggregated.

## Data (from `probe.json`: metadata and bucket columns only, no outcomes)
- New sets with official 17Lands Premier Draft Public Game Data, in release order:
  EOE (2025-08-01), TLA (2025-11-21), ECL (2026-01-23), TMT (2026-03-06), SOS (2026-04-24), MSH (2026-06-26), HOB (2026-08-14).
  SPM has no Premier Draft file.
- The HOB file was last modified on 2026-09-03, so its window is about 20 days rather than 28. The window is truncated, not padded.
- `user_game_win_rate_bucket` exists for NEO–TDM (16 of the 21 research sets) and for all new sets. It is missing for KHM, STX, AFR, MID and VOW.
- Aggregation is done by `scripts/case6_aggregate.py`, which uses the same card logic and 28-day window as the stored data.
  Check: its `all` group must reproduce the stored `compact_28d` games and wins for the 21 research sets exactly.
- New-set features are built by `scripts/case6_features.py`, which calls `card_features` unchanged.

## Part A: add newer sets to training (forward test)
- Model: the adopted baseline, unchanged. Features are the same; the model is ET 70% + TF-IDF/Ridge 30%, ×1.25 around the training mean. Seeds are 20260922–24.
- Each new set k is predicted by two arms:
  - Arm A trains on the 21 research sets.
  - Arm B trains on the 21 research sets plus every new set released before k.
- Decision sets: TLA, ECL, TMT, SOS, MSH, HOB. EOE is reported only, because A = B for EOE.
- **Rule A.** B is adopted for the next production retrain only if all of the following hold. Each is a 3-seed mean over the 6 sets unless stated.
  1. Within-set MAE improves.
  2. Within-set Spearman does not fall.
  3. MAE improves in at least 4 of the 6 sets (seed 20260922).
  4. The MAE gain exceeds arm A's seed-to-seed range.

## Part B: C3 on the new sets (the leakage check for proposal 1)
- New-set cards are extracted blind with the unchanged `research/gih_llm_extract/RUBRIC.md` and the same procedure: names hidden, order shuffled.
  A text already extracted is reused. Extraction is finished and committed before any new-set outcome is read.
- Arms: B (extended training, baseline features) vs B + C3, forward-chained as in Part A.
- **Clean test = MSH and HOB.** The extractor's knowledge ends in late June 2026.
  MSH was released 2026-06-26, so its play and results come after that. HOB was released 2026-08-14 and is entirely after it.
  EOE–SOS are reported separately and carry the same caveat as the 21-set backtest.
- **Rule B.** Proposal 1 is confirmed on post-cutoff data if, on the 3-seed mean over MSH and HOB, C3 improves both within-set MAE and within-set Spearman compared with B.
  Per-set results are reported. FRA remains the second prospective check.

## Part C: top-player GIH WR as a target
- Primary target: GIH WR in games by players with `user_game_win_rate_bucket` ≥ 0.60 and `user_n_games_bucket` ≥ 50 (`top60n50`). The window is the same as above.
  A card is included if it has at least 500 such games.
  Sensitivity targets: `top56n50`, `top64n50`, `top60`.
- Caveat: the bucket is the player's win rate over the whole dataset, including the games counted here. The group's overall level is therefore inflated.
  What matters is the difference between cards within a set.
- **C1, descriptive:**
  - share of games in the top group
  - top-group vs overall mean
  - within-set Spearman(top, overall)
  - split-half reliability by `draft_id` halves (Spearman-Brown), for both targets
  - the correlation between the targets corrected for that unreliability
- **C2, modelling:** LOSO over the 16 research sets that have the bucket, 3 seeds, with these arms:
  - T0: the adopted model trained on overall GIH, then shifted by the training-fold mean of (top − overall).
  - T1: the same model trained on top-player GIH directly.
  - T0 + C3 and T1 + C3 are reported as well.
- **Rule C.** A dedicated top-player model is worth building if T1 beats T0 on within-set MAE and Spearman against top-player GIH (3-seed mean), and wins on MAE in at least 9 of the 16 sets.
  Otherwise, predicting overall GIH and shifting it is just as good.
  The chosen arm is also run forward on TLA–HOB as a check; this is reported, not used for the decision.
- Whether the site shows a top-player forecast is the user's decision.
