# Case 4: two-stage colour-strength correction (pre-registered)

Research only; Pages unchanged. FIN, MH3, FRA outcomes not used. No 17Lands API calls. Written and committed before any result is computed.

## Idea
Stage 1 predicts each card. Stage 2 estimates, per set and colour, how much that colour's cards are over- or under-predicted, from colour-level aggregates of the set's own card pool, and adds a shrunk correction. Unlike C2 (rejected; card-level ability × environment features), this is one term per colour.

## Data
- Stage 1 = `research/production_c3/oof_28set.csv.gz` (production model, 28-set leave-one-set-out OOF). Card attributes from the same training pool (colours, rarity, C3 `llm_removal`).
- Colour membership: a mono-coloured card belongs to its colour. A multicolour card gets the mean of its colours' corrections. Colourless cards and lands get 0.

## Stage 2 features (per set × colour, W U B R G; card attributes and stage-1 predictions only; each centred within set across the 5 colours)
- f1: mean of the 5 highest stage-1 predictions among that colour's mono-coloured commons and uncommons
- f2: number of that colour's mono-coloured commons with `llm_removal` ≥ 2
- f3: mean stage-1 prediction of that colour's mono-coloured commons and uncommons
Features standardised on the training sets.

## Target and fit
- Target per set × colour: mean of (actual − pred) over that colour's mono-coloured cards (all rarities), centred within set across the 5 colours.
- Ridge regression, alpha = 1.0, no intercept (the targets are centred), fitted on the other 27 sets (135 rows), applied to the held-out set (leave one set out).
- Adjusted prediction: pred + λ · (the card's colour correction), **λ = 0.5**.
- Sensitivity (reported, not used for the decision): λ = 0.25 and 1.0; an oracle using the true held-out colour residuals (upper bound).

## Rule C
Case 4 is supported if, over the 28 sets, λ = 0.5 improves **all** of:
1. pooled MAE (pp)
2. mean within-set Spearman
3. MAE in at least 16 of the 28 sets.

If supported: compute the FRA correction from the production FRA predictions and freeze it; adoption is the user's decision.
