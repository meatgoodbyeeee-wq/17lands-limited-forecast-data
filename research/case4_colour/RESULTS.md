# Case 4 results: two-stage colour-strength correction

Research only. Pages unchanged. The plan (`PLAN.md`) was committed before this was run.
Reproduce: `python3 research/case4_colour/case4_colour.py` (outputs `result.json`, `colour_table.csv`).

## Rule C: **not supported**
28 sets, 7,075 cards; stage 1 = production 28-set OOF.

| | MAE (pp) | mean within-set Spearman | sets with better MAE |
|---|---|---|---|
| pred | 2.392 | 0.562 | – |
| **λ = 0.5** | 2.393 | 0.562 | 16 |
| λ = 0.25 | 2.392 | 0.562 | 16 |
| λ = 1.0 | 2.395 | 0.561 | 13 |
| oracle (true colour residuals) | 2.251 | 0.620 | – |

## Why
- The colour effect is real: the per-set colour residual has an SD of 1.04pp, and knowing it would reduce MAE by 0.14pp.
- The pool aggregates do not predict it. The correlation between stage-2 predictions and the true colour residual is 0.06. The individual features' correlations with the target are f1 +0.11, f2 (common removal) −0.16 and f3 +0.11. They are weak and partly cancel.
- The negative sign on common removal suggests the card-level model already credits removal fully.
- Averaged over sets, red is over-predicted (−0.48pp) and white and green are under-predicted (+0.29 and +0.23pp). This is a small and unstable pattern, and it was not tested as a rule.

## Conclusion
Colour strength cannot be read from the card pool with these simple aggregates. The gap to the oracle likely depends on things only visible after release, such as the metagame, archetype balance and gold-card support. Nothing is frozen for FRA.
