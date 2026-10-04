# C6: vocabulary gap tags — result (Rule F6, pre-registered): not supported

16 binary tags for mechanics the C5 vocabulary and the production baseline cannot express (poison, proliferate, −1/−1 counters, defender, transform/day-night, graveyard hate, noncreature removal, damage prevention, monarch/initiative/ring/goad, alternative costs, face-down, saga, class/room, lifegain, protection/indestructible, legendary), set by fixed text rules (`c6.py`, `RULES`; committed before scoring). Prevalence: legendary 15.6%, lifegain 7.3%, noncreature removal 4.3%, alt cost 3.1%, protection 2.2%, … prevention 0.2% (`prevalence.json`). 28 sets, leave one set out, production model, B6 with seeds 20260922–24.

| arm | pooled MAE (pp) | mean within-set Spearman | sets lower MAE vs B5 |
|---|---|---|---|
| A production | 2.392 | 0.562 | – |
| B = A + C4 | 2.353 | 0.578 | – |
| B5 = A + C4 + C5 | 2.2918 | 0.6061 | – |
| **B6 = B5 + gap tags** | **2.2909** | **0.6075** | **18 / 28** |
| B6 without C4, reported | 2.301 | 0.603 | 7 |
| B5 + tags with prevalence ≥ 1% (10), reported | 2.2912 | 0.6067 | 17 |

Rule F6 (B6 vs B5): MAE lower ✔, Spearman higher ✔, ≥ 15 sets ✔ (18), MAE gain > 0.01 pp ❌ (0.0009 pp) → not supported. By rarity the change is within ±0.007 pp.

Reading: the gaps were real in the sense that the labels could not say these things, but filling them does not improve the forecast. The affected cards are few (most tags under 5%), and the information they add is mostly already carried by the baseline's text flags and by the existing tags (CD, DW, SA, IN, RE, EQ). B5 remains the best card model; the gap tags are not carried forward and nothing new is frozen for FRA. Pages and production unchanged.
