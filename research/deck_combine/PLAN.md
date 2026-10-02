# Deck colour: combining the rejected ideas — pre-registered (Rule M)

Research only; Pages unchanged. Written before the combined models are run. No new data: it reuses the pair-level feature tables of steps 2, 3 and improvement 4 (both versions).

## Inputs (26 sets x 10 pairs, each already centred within set)
- F0 current formula; F1–F6 (deck_model); S draft-simulation score (variant `S`, draft_sim); R1–R5 (archetype_roles, theme proxy); A1–A5 (archetype_labels, official archetype labels).
- Not used: improvement 1 and 2 (card-level), case 4 (colour-level, not pair-level), ALSA (21 sets only).

## Candidates (fixed now)
- M1 ensemble: mean of the within-set standardised LOSO predictions of D (F1–F6), A (F1–F6+A1–A5), and S, and F0.
- M2 ensemble without F0: D, A, S.
- M3 one ridge on F1–F6 + A1–A5 + S, alpha 10 (stronger shrinkage because there are 260 rows).
- M4 same with alpha 30.
Same leave-one-set-out scheme as deck_model (ridge on standardised features, scaling re-fit per training fold; ensemble members are each produced by their own LOSO fit, so no test-set information enters).

## Rule M
A candidate is supported if (1) mean within-set Spearman ≥ max(D, A) + 0.02 and ≥ F0 + 0.05, (2) it beats F0 in ≥ 15 of 26 sets, (3) its MAE is below F0's. Reported: all four candidates, per-set counts, and Spearman of each member.
Caveat: the 26 sets have now been used for many ideas, so even a pass is only a candidate for a prospective FRA freeze, not adoption.
