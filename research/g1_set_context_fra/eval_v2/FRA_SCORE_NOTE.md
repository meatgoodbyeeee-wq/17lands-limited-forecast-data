# G1 v2 FRA score (run once, 2026-10-26 JST)

- Actual: `fra_actual_public_20261017.csv`, made from 17Lands Public Game Data (FRA PremierDraft, Last Updated 2026-10-17) with `scripts/aggregate_17lands.py` (same script as the past sets; per-game presence incl. tutored, draft_time window, >= 500 GIH games). Source sha256 a350666b…, 297,964 games, 276 cards; 271 matched to the frozen file (5 basic lands unmatched).
- **Post-hoc change (user decision, 2026-10-26):** PLAN/PENDING_FRA pre-registered the full 28-day window (2026-09-29 to 10-26). The public file ends around 2026-10-17 (about 18 days), like HOB. The user decided to score now on this data instead of waiting.
- `g1v2_score.py --actual fra_actual_public_20261017.csv` was run exactly once. Outputs: `fra_score_v2.json`, `fra_score_cards_v2.csv`, `grade_moves_v2.csv`.
- Verdict: F1 true, F2 false, F3 true → adopt_proposal false.

## G1 arm 2 (reference, run once, same actual CSV)
- `g1_score.py --actual fra_actual_public_20261017.csv --arms arm2` (only arm 2 is frozen). Outputs `fra_score.json`, `fra_score_cards.csv`.
- vs arm0 (B10): MAE −0.0016, Spearman −0.0007, top-10 under −0.003, top-20 under +0.016 → criteria: MAE true, Spearman false, top-20/10 false → not supported (practically no change).

## Post-hoc: past 28 sets without the scale conversion (exploration after the FRA score)
`g1v2_pred_eval.py --no-conv` (same as §14 but alpha=0, beta=1). Outputs `pred_eval_noconv.json`, `_cards.csv.gz`, `.log`.
B_rm (352 R/M): MAE −0.121 (conv −0.127), top-20 under −1.02 (conv −0.31), top-10 −1.02 (conv −0.25), Spearman +0.002 (conv +0.004), mean bias −0.92 (conv −0.33).
Reading: removing the conversion mostly raises the judged cards' predictions by about 0.9pp as a block; MAE and ranking do not improve beyond the converted version.
