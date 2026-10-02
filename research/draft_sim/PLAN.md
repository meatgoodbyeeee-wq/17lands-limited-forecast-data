# Deck colour step 3: draft simulation (pre-registered)

Research only; Pages unchanged. Same data and evaluation as step 2 (`research/deck_model`): 26 sets × 10 pairs, pair WR = unsplashed two-colour decks, 28-day window.
Card values are the production 28-set **OOF** predictions (pre-release information only). Written before any simulation is run.

## Simulation (per set, 300 pods, seed 20261002)
- Pool: the set's cards in the training pool, basic lands excluded. v = OOF GIH prediction (pp); m = set median of v.
- Packs: 10 commons, 3 uncommons, 1 rare slot (mythic with probability 1/8), drawn uniformly within rarity. 8 drafters, 3 packs, passing left/right/left, all 14 picks taken.
- Pick rule: score = (v − m) + γ·bonus, **γ = 4**.
  - Colour shares s_c = W_c / ΣW, where W_c = Σ max(v − m, 0) over the drafter's picks containing colour c (bonus 0 while ΣW = 0).
  - bonus = 2 · mean over the card's colours of s_c (capped at 1). Colourless cards get bonus 1.
- Deck: for each of the 10 pairs, the 23 highest-v cards among the drafter's picks that fit the pair (colours ⊆ pair) or are colourless non-land. Missing slots are filled with m − 3. Deck value = mean v of the 23. The drafter plays the pair with the highest deck value.
- Pair score S = mean deck value of the drafters who played that pair. If fewer than 20 drafters in all pods played it, use the mean deck value of that pair over all drafters.

## Evaluation (as step 2)
- Target: pair WR minus set mean. Within-set Spearman with S, mean over 26 sets; MAE after an OLS scale fitted leave one set out (S centred within set).
- Baseline F0 = current formula (step 2: Spearman 0.348, MAE 1.779).

## Rule S
The simulation is supported if, over 26 sets, it:
1. raises mean Spearman by ≥ 0.05 over F0;
2. beats F0 in at least 15 of 26 sets;
3. lowers MAE versus scaled F0.

Reported only: γ = 2 and 8; the simulation with actual card GIH as v (ceiling); the share of drafters per pair (simulated popularity) against real 17Lands deck counts.
