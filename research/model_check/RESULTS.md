# Is the B10 model class adequate? (2026-10-29, exploratory)
Same features (B5 numerics + g3, g3_z), tree part only, 1 seed, 28-set LOSO, centred within-set metrics, 17 eval sets:
| arm | MAE | Spearman | sd ratio | top-decile MAE |
|---|---|---|---|---|
| ExtraTrees, absolute target (B10's tree) | 2.261 | 0.622 | 0.64 | 3.76 |
| ExtraTrees, within-set target | 2.261 | 0.623 | 0.63 | 3.80 |
| HistGradientBoosting, within-set target | 2.258 | 0.620 | 0.67 | 3.68 |
Model class / target choice changes nothing (<=0.003pp). B11g residual vs G3 within set: Spearman 0.03 (G3 is used fully); slight top compression (g3>=3.5: actual - pred = +0.48pp).
Reference ceiling, 13 expert-graded sets, Spearman with actual: expert 0.635, B10 0.614, G3 0.495, C9 0.402. X1: adding expert grades to B10 = -0.08pp.
Set-mean error: raw MAE 2.231 vs centred 2.175 (B10).
