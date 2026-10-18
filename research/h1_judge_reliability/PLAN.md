# H1 — judge reliability and Haiku feasibility (pre-registered, Rule F19)

Committed before any re-judging. Descriptive study, no model fits, no production / Pages change. Never uses human evaluations.

## Question
(1) How reproducible is the A2 per-deck judgement (OFF / ON / P) when the same Opus judge reads the same input again?
(2) Can Haiku replace Opus for this judgement (cost)? (3) Would averaging several judges help?

## Data
Subset: 30 of the 290 A2 cards (the 8 named cards + 22 drawn with seed 20261018, subset.csv) × their 3 A2 decks = 90 decks.
Inputs are the unchanged A2 judge_in files and the unchanged EVJUDGE.md task text (enabler lists reused as-is).
Runs: run1 = original A2 Opus judgement; run2 = Opus again (9 agents × 10 decks, independent, read the WHOLE file);
run3 = Haiku (9 agents × 10 decks, same prompt). Agents must not see other runs' outputs.

## Measures (deck level, n = 90; card level = mean of the card's 3 decks, n = 30)
- Pearson r and Spearman of ON, OFF, P, EV between runs; mean absolute difference; mean bias (run − run1).
- Card level: within-set Spearman needs more than 30 cards, so use pooled Spearman and Pearson of card EV vs actual GIH (centered by set mean) for run1, run2, Haiku, mean(run1, run2), and mean of all three.
- ON gap: mean ON of Rite of the Dragoncaller − mean ON of Avengers Assemble! in each run (descriptive).

## Rule F19 (descriptive verdicts)
- Opus reproducible: Spearman(EV run1, run2) >= 0.75 at deck level AND card-level mean abs difference in EV <= 0.5.
- Haiku acceptable: Spearman(EV Haiku, EV run1) >= Spearman(EV run1, run2) − 0.05 AND |mean bias of ON| <= 1.0 AND
  card-level EV correlation with actual (set-centered) not lower than run1's by more than 0.05.
- Averaging helps: card-level correlation with actual of mean(run1, run2) exceeds each single run's by >= 0.03.
Outputs feed the choice between pre-registered follow-ups F (reference-card anchored judging) and G (pairwise comparison); nothing is adopted.
A1 cards shaped the method (flagged: the named cards are in the subset on purpose).
