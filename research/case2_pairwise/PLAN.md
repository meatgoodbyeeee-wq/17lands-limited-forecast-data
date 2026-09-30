# Case 2: in-set ranking by the LLM, turned into Bradley–Terry scores

Research only; Pages unchanged. This plan and the groups are committed before any ranking is made.
FIN, MH3 not used. No 17Lands API calls.

## Leakage control
The extractor (Claude, configured model `claude-opus-5-5`, knowledge to late June 2026) may know past sets' 17Lands numbers and reviews,
so only sets it cannot know are used:
- **HOB** (released 2026-08-14): fully after the cutoff — primary validation set.
- **MSH** (released 2026-06-26): at the cutoff boundary; its play happened after it — second validation set.
- **FRA** (released 2026-09-29): prospective. Scores and adjusted predictions are frozen and committed before FRA 17Lands data is visible (Card Data from 2026-10-13, Public Game Data later), then scored on the 28-day Public Game Data.

## Rankings
- Cards: HOB 184, MSH 278 (the cards with ≥500 GIH games and features, as in case 6), FRA 290 (full draftable pool).
- Groups of 8 cards from the same set. Each card appears in 3 groups (3 shuffles with seed 20261001, each cut into groups of 8; a short last group is merged into the previous one).
- The extractor sees mana value, colours, type line, P/T and rules text, with the card name replaced by `~`. Rarity, set name and all 17Lands numbers are hidden. Group order is shuffled across sets.
- Question for each group: "In a Premier Draft of this set, rank these cards from strongest to weakest by how much they increase your win rate when drawn (GIH WR)." Output: labels best → worst.
- Scores: Bradley–Terry fitted per set from all implied pairwise results (MM algorithm, prior of 0.5 win/0.5 loss against a virtual average card). Score = log-strength, standardised within set (z).

## Combination (fixed, no fitting)
`adjusted = (1 − w)·pred + w·(mean(pred) + sd(pred)·z)` within the set, **w = 0.3**.
`pred` = the honest forward prediction for HOB/MSH (case 6 arm B_extended+C3, 3-seed mean), the published production prediction for FRA.
Sensitivity (reported, not used for the decision): w = 0.15, 0.5, 1.0 (BT alone).

## Rule P
Case 2 is supported if, on the mean over HOB and MSH, `adjusted` (w = 0.3) improves **both** within-set MAE and within-set Spearman versus `pred`.
Reported: per set; HOB alone; Spearman of BT z alone vs actual GIH WR; split-half consistency (the 3 replicates).
FRA: frozen now; whether the site uses the adjustment is the user's decision after Rule P and the FRA check.
