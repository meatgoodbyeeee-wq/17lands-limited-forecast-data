# G4 pilot: outcome-based lessons to predict where B10 is wrong (pre-registered 2026-10-29, before any result)
Idea: G3 learned to imitate experts (ceiling ~ expert level, X1 says expert adds only -0.08pp). G4 learns from OUTCOMES:
from past sets, the cards where B10 missed most (actual - B10, within set), with the expert grade shown so Opus can see
when experts missed too. Opus writes general lessons (lessons_outcome.md). Then, for a whole target set, Opus sees each card
with B10's prediction (pp vs set mean, rank) and outputs an adjustment in pp (default 0) = where B10 is likely wrong.
Lesson sets: the 11 G3 lesson sets (BLB DFT DSK EOE FDN LCI MKM OTJ SOS TDM TLA). Targets: FRA, TMT, ECL (never in lessons).
Residual base: B10 (OOF for TMT/ECL, frozen pre-release prediction for FRA). 1 pass per target set.
Metrics per target set: Spearman(adj, B10 residual); combo y = B10 + k*adj with k fitted on the other two target sets (LOSO).
PASS if: Spearman(adj, residual) > 0.10 on >= 2 of 3 sets AND pooled combo MAE improves over B10 by >= 0.03pp.
Also reported: top-decile MAE, Spearman with actual. Answer keys are kept in keys/, never in the judge folders.
