# E1 results — Rule F18: no candidate passes

Top-10 (by actual GIH WR) of each set, 28 sets, 280 cards. B10 is the reference.

| model | T_bias pp | T_mae pp | Hit@20 | pooled MAE | sets T_mae lower | T_mae gain |
|---|---|---|---|---|---|---|
| prod_C3 | −5.44 | 5.46 | 0.607 | 2.392 | 1 | −0.85 |
| B10 | −4.59 | 4.61 | 0.696 | 2.231 | – | – |
| B11 | −4.58 | 4.60 | 0.682 | 2.233 | 16 | +0.008 |
| B12 | −4.59 | 4.61 | 0.700 | 2.230 | 15 | −0.003 |
| B13 / B13r | −4.60 / −4.61 | 4.62 / 4.63 | 0.693 / 0.696 | 2.232 / 2.231 | 12 / 12 | −0.009 / −0.020 |
| B14 | −4.76 | 4.77 | 0.693 | 2.262 | 8 | −0.157 |
| B15r | −4.58 | 4.60 | 0.696 | 2.226 | 12 | +0.009 |
| B15a | −4.58 | 4.60 | 0.696 | 2.230 | 17 | +0.008 (control +0.009: fails) |
| B16r | −4.59 | 4.61 | 0.689 | 2.228 | 9 | −0.001 |
| B16a | −4.59 | 4.60 | 0.700 | 2.230 | 18 | +0.004 (control +0.004: fails) |

Findings
- The top-end gap is untouched by every candidate: the actual top-10 of each set is under-predicted by ~4.6 pp in all of them (spread across candidates 0.17 pp, B14 aside).
- Best top-end moves (B11, B15r, B15a) are ~0.01 pp, the same order as the shuffled controls; B15a and B16a fail only the control.
- B14 raised the named bombs but also raised false tops (see below) and worsened everything else.
- Named cards (actual rank in set → B10 / B15r / B16r / B14 rank): Avengers Assemble! 6 → 260 / 198 / 231 / 42; Agent Phil Coulson 8 → 116 / 52 / 55 / 35;
  Chronicle of Victory 8 → 220 / 129 / 170 / 123; Necroduality 17 → 219 / 207 / 211 / 213; Arahbo 15 → 5 / 5 / 5 / 2.
  False tops: Rite of the Dragoncaller (actual rank 227) → 183 / 79 / 101 / 34; Smile at Death (227) → 87 / 55 / 62 / 40.
- Reading: A2/A3 EV moves the right cards up (AA 260→198, Phil 116→52) but moves Rite and Smile up as much; the metric confirms the
  separation problem is in the judged strength (ON), not in P or in the pooled-MAE yardstick.
Metric designed after seeing A2/A3; A1 cards shaped the method. No production / Pages change.
