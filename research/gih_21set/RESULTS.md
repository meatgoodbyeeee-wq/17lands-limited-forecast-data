# 21-set GIH research: results (2026-09-27)

Runs: snapshot/baseline 36302880273, comparison 36303227488. FIN not used. MH3 not used. Pages is unchanged.

## Baseline (adopted model, 21 sets)
- Reproduces run 36226176884 exactly: pooled MAE **2.49330pp**, Spearman **0.50884**.
- Within-set means: MAE 2.491, Spearman 0.522, top-10% bias −4.60pp, bottom-10% bias +5.18pp, strong recall 0.484, weak recall 0.351, pred SD / actual SD 0.524.
- Residuals are flat across predicted deciles but run from −5.3pp to +4.6pp across actual deciles. The error is missing information, not miscalibration.

## Comparison (3 seeds; mean, with baseline seed-to-seed range in brackets)

| config | pooled MAE | within Spearman | tail bias sum | recall mean | per-set MAE / ρ wins (seed 0) |
|---|---|---|---|---|---|
| baseline | 2.4931 [0.0013] | 0.5219 [0.0005] | 9.782 [0.007] | 0.415 [0.009] | – |
| C1 condition/efficiency | **2.4880** | **0.5232** | **9.708** | 0.416 | 10 / 11 |
| C2 ability × environment | 2.4961 | 0.5200 | 9.795 | 0.418 | 8 / 8 |
| C1+C2 | 2.4862 | 0.5236 | 9.709 | 0.415 | 15 / 12 |

## Verdict under the pre-registered rule (PLAN.md)
- **C1: not promising.** It passes rules 1, 2, 3 and 5: gains are larger than seed noise.
  It fails rule 4, set stability. It improves only 10/21 sets on MAE and 11/21 on Spearman; at least 12 were required.
  The gain is also small: −0.005pp MAE, and top-10% bias moves only from −4.60 to −4.54pp.
- **C2: rejected.** MAE and Spearman are both worse.
- **C1+C2: not eligible.** C2 failed on its own. Its 15/21 set wins are recorded but not used as a basis for decisions.

## Conclusion
Neither candidate meaningfully reduces tail compression. Production stays as it is. Stopping this line here keeps within the "at most 2 candidates" limit.
Supplementary, post-hoc, not decision-grade: with the 3 seeds averaged per set, C1 wins 13/21 sets on MAE and 10/21 on Spearman.
