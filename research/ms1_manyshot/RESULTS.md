# MS1 results (2026-10-26): FAIL on both pre-registered test sets

R/M only, Δ = GIH WR minus set mean of scored cards (pp). MS = mean of 3 Opus passes.
Blend = 0.5·B10 + 0.5·MS (fixed from the pilot).

| set | n | Spearman B10 | Spearman MS | MAE B10 | MAE MS | MAE blend | ΔSpearman 95% CI | pass |
|---|---|---|---|---|---|---|---|---|
| MSH (pilot, not counted) | 82 | 0.595 | 0.685 | 2.758 | 2.642 | 2.575 | −0.01 … +0.20 | (yes) |
| HOB | 59 | 0.729 | 0.636 | 3.272 | 3.464 | 3.274 | −0.20 … +0.00 | no |
| FRA | 85 | 0.645 | 0.562 | 3.028 | 3.198 | 3.012 | −0.18 … +0.00 | no |

- On both test sets MS ranks R/M worse than B10 (−0.09 / −0.08); the blend is no better than B10
  in MAE (HOB +0.002, FRA −0.016, both within noise).
- The pilot gain on MSH did not replicate; with ~60–85 cards per set, a ±0.09 Spearman swing is
  within the set-to-set noise (CIs above).
- Passes agree strongly (0.95–0.97), so the judgement is stable but not more accurate than B10.
- Top-10 under-prediction shrinks slightly with the blend (HOB 4.5→4.1, FRA 6.3→6.0pp), not enough.
- Tokens: ≈185k per pass, 9 passes ≈ 1.67M.
Conclusion: showing ~800 outcome-labelled examples does not make Opus a better R/M forecaster
than B10. Not adopted for TRK.
