# D10: AI reads the whole FRA set and judges the 10 colour pairs — pre-registered (prospective, FRA only)

Research only; Pages and production unchanged. Written before any judgement was made. No FRA outcome data is used (FRA early 17Lands data is not shown to the readers; they have no web access).

## Why
D9 showed that the colour effect B5 misses is the part of colour strength that is not an aggregate of card quality (format speed, how archetypes work, signpost synergy). A reader who sees the whole set at once can judge that. On historical sets an AI reader may remember the outcomes, so the only clean test is a new set: FRA (released 2026-09-29, after the reader models' knowledge).

## Method
`fra_cards.txt`: all 280 FRA booster cards except basic lands, with rarity, MV, colours, type, P/T, rules text, names replaced by "~". Three independent reading agents (r1, r2, r3) follow `TASK.md`: each reads the whole list and gives every pair a score 0–10 and a rank. No agent sees another's output. The frozen prediction is the mean score over the three readers (`pred_AI`); also frozen: each reader's scores, agreement between readers.

## Test (at the 10/28 FRA check, PENDING_FRA item 9)
Target: centred FRA pair win rate (Premier Draft, 28-day window, non-splash two-colour decks, as research/deck_pair). Within-set Spearman over the 10 pairs for pred_AI, pred_D_B5 and F0_A (item 8), and for the mean of the within-set z-scores of pred_AI and pred_D_B5 (combination). One set, 10 pairs: indicative only (a Spearman difference needs about 0.3 to mean much). Adoption, and whether to repeat on the next sets, is the user's decision.
