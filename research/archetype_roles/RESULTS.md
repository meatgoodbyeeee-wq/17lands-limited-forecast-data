# Improvement 4: archetype-role features — result (Rule R, pre-registered): not supported

26 sets x 10 pairs, leave one set out, ridge alpha 3. Archetype signal = existing blind C3 theme/dependency labels (no new role labelling was run; see PLAN.md).

| | mean within-set Spearman | MAE of centred pair WR (pp) |
|---|---|---|
| F0 current formula | 0.348 | 1.779 |
| D: F1–F6 | 0.418 | 1.788 |
| **R: F1–F6 + R1–R5** | **0.381** | 1.803 |
| R1–R5 only | 0.070 | 1.929 |

Rule R: Spearman ≥ F0 + 0.05 and ≥ D ❌ (0.381 < D 0.418); better than F0 in 13/26 sets ❌ (need 15); MAE lower ❌ → fails. Alpha 1/10 gives 0.379/0.383.

Single features (Spearman): theme concentration −0.13, gold build-arounds 0.02, net impact 0.03, friction −0.15, top-theme quality 0.04. The archetype features alone carry no signal, and adding them makes the model worse than D.

Reading: theme-dependence labels from card text do not explain which colour pairs win. Combined with improvements 1–2 and steps 2–3, the pre-release card information seems to hold little pair-level signal. A dedicated role labelling remains untested, but this result lowers its expected value. Pages and production unchanged; nothing frozen for FRA.
