# Deck colour step 3 results: Rule S not supported

Research only; Pages unchanged. The plan was committed before any simulation was run.
Reproduce: `python3 research/draft_sim/draft_sim.py` (about 7 minutes; outputs `result.json`, `sim_pairs.csv`).
26 sets, 300 pods per set (2,400 simulated drafters).

| | mean within-set Spearman | MAE (pp) | sets better than F0 |
|---|---|---|---|
| F0 current formula | 0.350 | 1.779 | – |
| **S: simulated deck value, γ = 4** | **0.132** | 1.919 | 7 / 26 |
| S, γ = 2 / γ = 8 | 0.080 / 0.229 | 1.972 / 1.883 | – |
| S with actual card GIH (ceiling) | 0.485 | 1.821 | – |

Rule S fails on all three criteria. The pre-registered fallback was used for 1 of 260 pairs.

## Why
In the simulation, strong colours attract more drafters, so each drafter's deck in a popular pair is *weaker*. The pre-registered score (mean deck value of the drafters who played the pair) therefore penalises the strong pairs. On 17Lands the opposite happens: popularity and win rate go together. The within-set Spearman of real deck count with pair WR is **0.67**, because players learn which pairs are good.

## Exploratory (not pre-registered, decides nothing)
Using the simulated **share of drafters** per pair as the score instead:
- OOF predictions: Spearman 0.42, better than F0 in 12 of 26 sets. This is no better than step 2's Ridge (0.42).
- Actual card GIH: 0.75, better than F0 in 22 of 26 sets.

Simulated popularity correlates 0.46 with real popularity.

## Conclusion
Turning card predictions into pair strength by simulation does not beat the simple formula. All three steps point the same way: the limit is the colour-level information in the pre-release card predictions themselves.
