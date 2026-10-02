# Deck colour step 2: new pair-strength model (pre-registered)

Research only; Pages unchanged. Uses step 1 data (`research/deck_pair`): 26 sets (KHM, STX have no deck colours), pair WR = unsplashed two-colour decks, 28-day window.
Inputs are pre-release only: card attributes, C3 LLM features, and the production 28-set **OOF** card predictions (each set predicted by a model that never saw it).
Written before any feature is computed.

## Card weights and fit
- Print weight per card: commons 10/nC, uncommons 3/nU, rares (7/8)/nR, mythics (1/8)/nM, where nX is the number of cards of that rarity in the set (from the training pool). Basic lands are excluded.
- A card fits a pair if its colours are a non-empty subset of the pair. Colourless cards and lands are excluded from pair features.

## Features per set × pair (each centred within set across the 10 pairs, then standardised on the training sets)
- F0 baseline: unweighted mean OOF prediction of fitting commons and uncommons (the current formula).
- F1: print-weighted mean OOF prediction of fitting cards (all rarities).
- F2 depth: print-weighted mean OOF prediction of the best fitting cards that make up the top half of the pair's print weight.
- F3 signpost: mean OOF prediction of commons and uncommons whose colours are exactly the pair (0 if none, before centring).
- F4 removal: print-weighted share of fitting cards with C3 `llm_removal` ≥ 2.
- F5 cheap creatures: print-weighted share of fitting cards that are creatures with mana value ≤ 2 and OOF prediction above the set median.
- F6 evasion: print-weighted share of fitting cards that are creatures with flying or menace.

## Model
- Target: pair WR minus the set mean of the 10 pair WRs (pp).
- Candidate D: Ridge, alpha = 3, no intercept, on F1–F6, fitted on 25 sets and applied to the held-out set (leave one set out).
- Baseline: F0 (Spearman needs no scaling; for MAE, F0 is scaled by an OLS slope fitted leave-one-set-out).

## Rule D
D is supported if, over 26 sets, it:
1. raises mean within-set Spearman by ≥ 0.05 over F0;
2. has a higher Spearman than F0 in at least 15 of the 26 sets;
3. lowers the mean absolute error of the centred pair WR versus scaled F0.

Reported, not used for the decision: each single feature's mean Spearman; Ridge on F0–F6; alpha = 1 and 10.
FRA: the early 17Lands pair WRs are already visible, so FRA is indicative only. If D is supported, its FRA prediction is shown next to the early data, and any site change is the user's decision.
