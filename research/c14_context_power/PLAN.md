# C14 — C9 power questions answered with the whole set in view (pre-registered before any judgement)

## Why (diagnosis, 2026-10-15)
Every model so far (production C3 51.7%, A, B5, B10 52.7%, all C4–C13 variants 51–53%) predicted Avengers Assemble! (MSH mythic, actual 64.5%, 6th of 278) *below* the set average (pred mean 55.7%; mythic mean pred 57.9%), although players widely expected it to be a bomb. Counterfactual on the B10 MSH fold (training unchanged, seed 20260922): with its real C9 readings (IMP 1.0, UNA 1.7, PLAY 1.3, GRADE 3.0) the prediction is 52.7%; with C9 readings of a bomb (IMP 3, UNA 4, VAL 3, FLOOR 2, FLEX 2, PLAY 4, GRADE 9) the same model predicts 59.2%. The C9 readers saw each card alone and had no way to know that 91/273 cards of the set are Heroes. C11–C13 added side information or capped corrections and left the base readings in place. C14 replaces the base readings themselves with readings made with the whole set list in view.

## Judgements
All 7,210 cards of the 29 sets (incl. FRA), one set per file, names hidden, rarity and freq shown (input/s1 in id order, input/s2 shuffled), RUBRIC.md = the seven C9 questions with the instruction to judge each card as it plays in this set. Two independent passes by different agents (s1, s2; an agent never sees the other pass). Caveat: readers may recognise historical sets; FRA is the clean test. 145 pool cards that are not in the set lists (as in C11) keep their original C9 values.

## Features
For each card: mean of s1/s2 for the seven questions (replacing c9_m_*), SD = population SD of the two passes (replacing c9_s_*), and the three C9 sums recomputed from the new means (replacing c9_impuna, c9_valfloor, c9_bomb). No extra columns.

## Arm
**B14** = B10 with these 17 columns replaced (3 seeds 20260922–24, LOSO over 28 sets, production model e.parts and ×1.25 formula).
Reported only (no rule): pass agreement; correlation with original C9; MAE for cards B10 under-predicted by > 5 pp and over-predicted by > 5 pp, targets of C11 vs others, by rarity; AUC for set top-10; predictions for Avengers Assemble!, Chronicle of Victory, Necroduality, Rite of the Dragoncaller, Smile at Death, Oko, Lorwyn Liege; rank of Avengers Assemble! in MSH.

## Rule F15 (versus B10 = 2.2311 pp / Spearman 0.6248)
Supported if pooled MAE lower, mean within-set Spearman higher, ≥ 15/28 sets lower MAE, and MAE gain > 0.01 pp. If supported: freeze FRA B14 predictions next to A, B, B5, B10 (new frozen file + sha256), add PENDING_FRA item 11, update the 10/28 scheduled verification. If not: FRA readings stay descriptive. No production/Pages change either way.
