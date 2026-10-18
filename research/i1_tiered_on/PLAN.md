# I1 — tiered ON with simulated enabler counts (pre-registered, Rule F21)

Committed before any judging. Pilot on the same 90 decks (30 cards) as H1/F1. No model fit, no production / Pages change, no human evaluations.

## Why
F1 showed the judge reads order correctly (OFF low, P reduced for Rite) but sets ON to the best case ("spells keep flowing"),
because ON was defined as "condition met as designed". I1 splits ON by how many enablers actually work with the target and asks for
the AVERAGE result in such games, including idle turns and late payoff; how often each case happens is computed, not judged.

## Judging
Same inputs as F1 (9 reference cards from other sets with measured pp + A2 deck + enabler list). Task text I1JUDGE.md (fixed).
Output OFF, ON1, ON2, ON3 in pp. 9 Opus agents × 10 decks, blind, read the WHOLE file, no listing of other outputs.

## Weights (build.py, seed 20261018, 20,000 games/deck, A3 model)
w0..w3 = share of games (target cast by turn 10) in which 0 / 1 / 2 / 3+ enablers work with it, A3 rules with ONE change decided
before judging (after looking at the simulated weights only): an AFTER enabler drawn before the target was cast counts only if held,
with hold probability 0.5 (A3 assumed every earlier draw was held, which gave Rite 3+ spells after it in 51–71 % of games).
Cost-reduction cards with cast rate < 0.05 (3 decks) use the F1 judge P: w0 = 1 − P, w1 = P.
EV_I = w0·OFF + w1·ON1 + w2·ON2 + w3·ON3 (pp); card value = mean of its 3 decks.

## Rule F21 (pilot supported)
Pass iff ALL: Pearson(EV_I, actual) >= 0.62; Spearman(EV_I, actual) >= 0.49 (at least F1's 0.489); EV_I(Rite of the Dragoncaller) < EV_I(Avengers Assemble!);
MAE(EV_I) < MAE of zero prediction. Descriptive: ON1 of Rite vs AA, named cards, EV_I with A3 hold-all weights.
Pass → expand to 290 cards with a new pre-registered plan, then model test (F16-style + F18 top-end). Fail → stop the judged-ON line.
Caveats: n = 30, one judge run; the named (A1) cards are in the subset on purpose and shaped the method.
