# Improvement 4: archetype-role features for deck colour (pair) strength — pre-registered (Rule R)

Research only; Pages unchanged. Written before any feature is computed.

## Idea
Pair strength depends on whether the pair's cards form a coherent archetype (payoffs with enablers, shared themes), which per-card quality averages cannot see.

## Scope and honesty note
A new LLM labelling of ~7,000 cards by archetype role is not run here. The existing blind LLM extraction (C3: `llm_dep_*` dependency themes T/G/A/E/S/K/C/L/X/H/M/O, `llm_dependency`, `llm_net`, `llm_impact`, `llm_friction`) already labels each card's theme dependence from rules text only. This test uses those labels as the archetype-role signal. If it is supported, a dedicated role labelling would be the next step; if not, it is weak evidence against it, not proof.

## Features (per set, pair; cards fitting the pair as in `research/deck_model`, lands and colourless excluded, rarity-pack weights w; each centred within set)
- R1 theme concentration: max over themes of the w-weighted share of fitting cards with `llm_dep_theme` = 1.
- R2 gold build-arounds: w-weighted share of cards of exactly the pair (two colours) with `llm_dependency` ≥ 1.
- R3 net impact: w-weighted mean `llm_net` of fitting cards.
- R4 friction: w-weighted mean `llm_friction`.
- R5 theme-weighted quality: mean prediction of cards in the pair's top theme (the theme of R1), zero-filled to the pair mean prediction when no card has it.

## Model
Same as step 2: ridge alpha 3 on standardised features, leave one set out, 26 sets x 10 pairs, target = centred unsplashed pair WR. Arm D (F1–F6) vs arm R (F1–F6 + R1–R5), compared with F0 (current formula).

## Rule R
R is supported if (1) mean within-set Spearman of R ≥ that of F0 + 0.05 **and** ≥ that of D, (2) R beats F0's Spearman in ≥ 15 of 26 sets, and (3) R's MAE < F0's MAE. Reported only: R-only features, alpha 1/10.
