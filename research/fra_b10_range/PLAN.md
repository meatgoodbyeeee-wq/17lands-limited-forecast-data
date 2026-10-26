# FRA B10 prediction range (M5), frozen before FRA outcomes (2026-10-26)

Purpose: the TRK preview uses the B10 point prediction with an 80% range refit on the 28-set leave-one-set-out B10 residuals (research/trk_preview/export_b10.py).
No FRA test of that range is registered in PENDING_FRA.md (item 5 only covers the production range). This freezes it for FRA now, from the frozen B10 predictions
(`research/c9_power_questions/fra_frozen_predictions.csv`, column pred_B10), so it can be scored with the other FRA items.

- Method: unchanged M5 (normalized conformal, research/production_c3/export_gih_c3_28set.py `cmd_range`) with the out-of-fold residuals of B10 (`oof_B10.csv.gz`) in place of the production ones, as in export_b10.py.
- No FRA outcome, no FIN/MH3 outcome is read. Output: `fra_b10_range.json` (+ sha256 in `fra_b10_range.meta.json`).
- Scoring (reported only, no pass/fail; with the other FRA items, 28-day Public Game Data, cards with >= 500 GIH games): share of cards whose observed GIH WR lies inside [lo, hi],
  overall and by rarity, mean width; next to the same numbers for the production range (`data/gih-range-fra.json` in the Pages repo). Target coverage 80%.
