# F1 — reference-anchored judging pilot (pre-registered, Rule F20)

Committed before any judging. Pilot on the H1 subset (30 cards × 3 A2 decks = 90 decks). No model fit, no production / Pages change,
no human evaluations or set reviews.

## Change versus A2
Same decks and enabler lists (A2 judge_in), same OFF / ON / P decomposition. The only change is the scale: instead of 0–10 grades the judge
(Opus, blind, no memory of real cards) sees 9 REFERENCE cards from OTHER sets (leave-one-set-out; text only, names hidden) with their measured
GIH WR in pp versus their set average (taken at quantiles 3,15,30,45,60,75,88,96,100 % of the 290 A2 cards of the other sets, build.py)
and states OFF and ON directly in pp on that scale. P is still the judge's estimate (variant with simulated P from A3 also reported).
Task text: F1JUDGE.md (fixed). Judging: 9 Opus agents × 10 decks, independent, read the WHOLE file, may not list/print other outputs.

## Measures (card level, n = 30; actual = set-centred GIH WR in pp)
EV_F = P·ON + (1−P)·OFF (pp). Compare with the H1 judges' EV (grades) whose card-level Pearson with actual was 0.56 (run1) and 0.56 (run2).
- Pearson and Spearman of EV_F vs actual; also of ON_F alone; MAE (pp) of EV_F vs actual (calibration, descriptive).
- ON_F(Rite of the Dragoncaller) − ON_F(Avengers Assemble!) in pp (descriptive and used in the rule).

## Rule F20 (pilot supported)
Pass iff ALL: Pearson(EV_F, actual) >= 0.62 (best H1 single run + 0.06); Spearman(EV_F, actual) >= 0.40 (H1 run1 0.37, run2 0.34, +0.03);
ON_F(Rite) < ON_F(Avengers Assemble!); MAE(EV_F vs actual) < MAE of a constant-zero prediction (i.e. it adds information).
Pass → expand to the 290 A2 cards with a new pre-registered plan (judging cost ~ A2 judging) and test as a model feature under Rule F16-style criteria
plus Rule F18 top-end metric. Fail → anchored judging does not fix the ON problem on this pilot; stop this line.
Caveats stated in advance: n = 30 is small; the 8 named cards (A1 cards, which shaped the method) are in the subset on purpose, so a pass is a
reason to expand, not evidence of generalisation.
