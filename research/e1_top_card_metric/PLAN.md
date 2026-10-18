# E1 — top-card metric (pre-registered, Rule F18)

Committed before computing. Offline re-scoring of EXISTING out-of-fold predictions only; no new model fits, no AI calls,
no production / Pages change. Never uses human evaluations or set reviews.

## Why
Rules F5–F17 judged candidates by pooled MAE over all 7,075 cards (needed gain > 0.01 pp). Candidates that touch only
~4 % of cards (A2/A3: 280 cards) cannot clear that bar even when they help those cards, while the stated goal is to
recognise bombs (e.g. Avengers Assemble!, actual 64.5 %, 6th of 278 in MSH). Pooled MAE is the wrong yardstick for that goal.
B10 under-predicts the actual top-10 of each set by ~4.6 pp (checked once before this plan, B10 only).

## Metrics (per set, then pooled over the 28 sets; actual = actual_gih, pred = OOF prediction)
- T_bias: mean(pred − actual) over the set's actual top-10 cards (pp). Primary: |T_bias| (smaller is better), pooled over 280 cards.
- T_mae: mean |pred − actual| over the actual top-10 (pp).
- Hit@20: share of the actual top-10 that are inside the predicted top-20 (higher is better).
- Hit@10: same with predicted top-10 (descriptive).
- Guards: pooled MAE (all cards), mean within-set Spearman, B_bias = mean(pred − actual) over actual bottom-10 (pp), and F_bias = mean(actual − pred) over the predicted top-10 (false-top check; a candidate must not improve T_bias merely by inflating everything).
- Regression to the mean makes T_bias negative for any model; candidates are compared against B10, not against zero.

## Candidates
B10 (reference), production C3 (oof_28set), B11, B12, B13, B13r, B14, B15r, B15a, B16r, B16a, and their shuffled controls where they exist
(shuf_B13, shuf_B13r, shuf_B15r, shuf_B15a, shuf_B16r, shuf_B16a).

## Rule F18 (per candidate vs B10)
Pass iff ALL: T_mae lower; Hit@20 not lower; |T_bias| lower; T_mae improves in >= 15 of 28 sets;
pooled MAE worse by at most 0.01 pp; F_bias not worse by more than 0.5 pp; and (where a shuffled control exists) the shuffled control's
T_mae gain is less than half of the candidate's.
Candidates that pass are "top-end supported" only as a diagnostic: nothing is adopted, FRA stays descriptive unless a candidate also
passes its own earlier rule; a pass here means "worth a pre-registered top-end-targeted follow-up".

## Reporting
Table for every candidate; named cards (Avengers Assemble!, Rite of the Dragoncaller, Smile at Death, Agent Phil Coulson,
Doubling Season, Arahbo, Necroduality, Chronicle of Victory) with actual / B10 / best candidate and their within-set ranks.
A1 pilot cards shaped the method and are flagged. Metric designed after seeing A2/A3 results — stated, not hidden.
