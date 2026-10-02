# FRA singularity baseline (descriptive only)

Set-level and card-level counters from the official 17Lands Public Game Data (Premier Draft) for past Standard sets,
used to put early FRA numbers in context for an article. Nothing here is used by any model or by the frozen FRA checks.

- `scripts/singularity_baseline.py` produces `data/{SET}_sets.json` (per-window game, turn, mulligan and colour counters)
  and `data/{SET}_cards.csv` (per-card deck / OH / GD / GND / GIH counts for windows D3 and D28).
- Windows are whole UTC dates of `draft_time` counted from the first date with at least 5,000 games.
- FRA and MH3 are refused by the script. FIN is included only because its one-time holdout check is already finished
  (`research/fin_final`); its numbers are descriptive here.
