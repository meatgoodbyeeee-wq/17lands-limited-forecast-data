# Deck colour step 2 results: Rule D not supported

Research only; Pages unchanged. The plan was committed before any feature was computed.
Reproduce: `python3 research/deck_model/deck_model.py` (outputs `result.json`, `pair_features.csv`).
26 sets × 10 pairs, leave one set out.

| | mean within-set Spearman | MAE of centred pair WR (pp) | sets better than F0 |
|---|---|---|---|
| predicting 0 for every pair | – | 1.944 | – |
| F0 current formula (scaled) | 0.348 | 1.779 | – |
| **D: Ridge on F1–F6** | **0.418** | 1.788 | 13 / 26 |

Rule D: Spearman gain ≥ 0.05 ✅; at least 15 sets better ❌; lower MAE ❌ → **not supported**.
Sensitivity: alpha 1 or 10 gives the same picture (0.418 / 0.415). Adding F0 to D gives 0.364.

## Single features (mean Spearman)
F0 0.35 · F1 print-weighted 0.33 · F2 depth 0.28 · F3 signpost 0.29 · F4 removal −0.04 · F5 cheap creatures 0.09 · F6 evasion 0.01.
Full-fit coefficients (standardised units): F1 0.51, F2 0.41, F3 0.53, F4 −0.18, F5 −0.05, F6 0.01.

## Reading
- Everything with signal comes from the card predictions: mean quality, depth and the signpost card. Counting removal, cheap creatures or evasion adds nothing. Removal again has a negative sign, as in case 4.
- Combining the card-quality views helps the average order somewhat (+0.07). It is not consistent across sets, and the size of the gaps does not improve.
- With actual card GIH, the plain formula reaches 0.62 (step 1). The bottleneck is the colour-level information in the card predictions, not the way they are combined.
