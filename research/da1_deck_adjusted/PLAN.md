# DA1 — deck-adjusted GIH as an explanation and as a training target (pre-registered, written before any DA1 computation)

Research only. Branch `research/da1-deck-adjusted` (from main, never merged). Production model, Pages and TRK files are not changed. FRA and TRK actuals are not read or aggregated. The only new data are 17Lands Public Game Data aggregates for the same 28 sets as `oof_B10.csv.gz`.

## Why
Part of B10's error may come from the deck and the player that used the card, not from card strength. Example (B10 OOF, N2b primary pairs): Shore Up is +2.5 pp above prediction in DMU and -0.9 pp in BLB, while the nearly identical TLA Octopus Form is +3.9 pp. Correlation with colour-pair win rate is 0.28 over all cards, and colour does not explain the Shore Up gap.

## Metric definitions (per card, per set)
Source: 17Lands Public Game Data, Premier Draft, same file, same window (earliest `draft_time` in the file + 28 days, `draft_time >= start and < end`) and same card definition as `scripts/aggregate_17lands.py` (a game counts for a card once if the card is in `opening_hand_*`, `drawn_*` or `tutored_*`). Cards with GIH games >= 500 (as in training). Sets = the 28 sets in `oof_B10.csv.gz`.
- **Raw GIH**: wins / games. Must equal `data/compact_28d/<SET>_gih_28d.csv` (games and wins) and `actual_gih` of `oof_B10.csv.gz`.
- **Deck-adjusted GIH (primary)**: mean over the card's GIH games of (won - deck baseline). Deck baseline of a game = win rate of the OTHER games with the same `draft_id` inside the window (leave-one-out: (draft wins - own won) / (draft games - 1)). Games whose draft has no other game are excluded (from the deck-adjusted mean only). Stored with its game count (`dadj_n`) and sum of squares.
- **Player-adjusted GIH (report only)**: mean of (won - `user_game_win_rate_bucket`); empty if the set has no such column.
- **Colour-adjusted GIH (report only)**: mean of (won - win rate of that game's `main_colors` over all games in the window of that set); empty if no `main_colors` column.
All adjusted values are in win-rate units (x100 = pp). Each is a mean over the games where the card was in hand, so they are directly comparable to the raw GIH and are NOT re-centred by card (the set mean over cards is subtracted only where stated).

## Aggregation (GitHub Actions; the sandbox cannot reach the 17Lands S3)
`scripts/da1_aggregate.py` (reuses the download and window code of `case6_aggregate.py`, two passes: pass 1 reads `draft_time, draft_id, won, main_colors` for all rows, pass 2 reads the card columns and computes per-card sums). `.github/workflows/da1_aggregate.yml`: matrix over the 28 sets, runs on push to this branch only (path filter on the script and the workflow), the last job concatenates the 28 outputs and manifests into `research/da1_deck_adjusted/data/da1_cards.csv.gz` + `da1_manifests.json`, commits to this branch. The workflow and aggregate script's trigger are removed after use. Each set job also asserts raw games/wins = `data/compact_28d` and writes the check into its manifest; a mismatch is reported (not hidden).

## A. Explanation (no pass/fail)
Pairs = the N2b primary definition (branch `research/n2-near-duplicate`; `n2b.py`/`prep.py` logic reproduced unchanged with the same inputs `cards.csv.gz`, `oof_B10.csv.gz`, creature rule cos >= 0.95 & equal mv & equal P/T, non-creature non-land cos >= 0.95 & |mv diff| <= 1, lands excluded). `n2b_cards_primary.csv` lists only the first 3 partners per card, so the full pair list is regenerated and checked against it (same 127 corrected cards). For each pair (c in S, d in S'): |(v_c - mean_S v) - (v_d - mean_S' v)| in pp, where mean_S is the mean over the cards of the set (>= 500 games). Report the mean over pairs for v = raw GIH, deck-adjusted, player-adjusted, colour-adjusted. Also the same for the three named cards (DMU Shore Up, BLB Shore Up, TLA Octopus Form), in a table with raw / deck / player / colour values (pp) and the set-centred values. "Between-set variance" over all cards (7,075): variance of the 28 set means (cards equally weighted) of raw and deck-adjusted GIH, the within-set variance (pooled), and the between share = between / (between + within).

## B. Prediction (Rule DA1)
Same features, same training code as B10 (`research/c9_power_questions/c9.py` arm B10 path: `c5.arm_nums('B5')` + MEAN + SD + SUM; `export_gih_c3_28set.parts`; ExtraTrees 600 leaf 8 max_features 0.6 + TF-IDF Ridge 10, 70:30, x1.25, seeds 20260922-24 averaged). First reproduce the `oof_B10` predictions for one set (and report max abs difference); then change ONLY the training target:
- y_DA1 = deck-adjusted GIH of the card minus the mean of that value over the cards of its set (centred within set).
- For test set s (LOSO, 27 training sets) the model predicts p_c (centred deck-adjusted units).
- Conversion to raw GIH units: b = slope through the origin of (raw GIH minus its set mean) on (y_DA1) over the training cards only (fitted on the training sets' actual values; in-sample predictions of the extra-trees are overfit, so they are not used for the primary; report-only variant: slope on the training sets' in-sample predictions). Final prediction = mean of B10's predictions in the evaluated set + b * (p_c - mean_s p_c). That is, the evaluated set's mean is exactly B10's (set-level error is identical by construction; only within-set values change).
- Evaluate against the raw `actual_gih`, same metrics as B10 (`c5.metrics`: pooled MAE pp, mean within-set Spearman, per-set MAE).

**Rule DA1** (all four): (1) pooled MAE of DA1 < B10's; (2) mean within-set Spearman of DA1 >= B10's - 0.0005 (i.e. not lower by 0.0005 or more); (3) DA1 has lower MAE than B10 in >= 15 of the 28 sets; (4) improvement (B10 MAE - DA1 MAE) > 0.01 pp.
Report only: average of B10 and DA1 predictions (same metrics); breakdown by rarity; the 10 cards B10 under-predicts most (actual - pred) with their DA1 prediction; the in-sample-slope variant. A pass means "worth a follow-up" only; nothing is adopted.

## Known limitations
- The deck baseline is the win rate of the same draft's other games: it mixes deck strength and player skill (and the same player's deck being strong because of the card itself). The leave-one-out baseline is noisy for drafts with few games (<= 9 games per draft; 1 other game gives a 0/1 baseline); this adds noise to all adjusted means.
- Window and available columns can differ by set (no `user_game_win_rate_bucket` or `main_colors` in some sets -> blank).
- Games with no other game in the draft are dropped from the deck-adjusted mean only, so its game count is a little smaller than raw.
- Centred targets remove the set-level information from training; set means rely on B10's.
- The OOF predictions used for A and B come from models that never saw the evaluated set's outcomes except through N2b's (A uses B10 OOF only to build the pairs).
