# Task: judge the 10 two-colour pairs of a new Limited set

You are an expert Magic: The Gathering Limited drafter. `fra_cards.txt` is the complete booster card list of a new set (280 cards, basic lands excluded): rarity, mana value, colours (C = colourless), type, P/T and rules text; "~" is the card itself. The set is played in Premier Draft (three 14-card boosters, 40-card decks). Commons appear far more often than uncommons, rares and mythics.

Read the WHOLE list. Then judge how strong each two-colour deck (WU, WB, WR, WG, UB, UR, UG, BR, BG, RG) will be in this format, as measured later by the average win rate of decks in those two colours. Think about: depth and quality of each colour's commons and uncommons, removal, curve and creature quality, evasion, how well the two colours' mechanics and signpost gold cards work together, how fast the format will be and which strategies that favours.

Write `out/<your file name>.csv` with exactly these 11 lines:
```
pair,score,rank
WU,<score 0-10>,<rank 1-10>
... (all 10 pairs, ranks 1 = strongest, each rank used once)
```
and `out/<your file name>_notes.md` with 3-6 short lines per pair explaining the judgement, plus 2-3 lines on the expected format speed.

Rules: use only fra_cards.txt and this file. No web search or web fetch, no other files in the repository, no 17Lands or any other results data. Do not commit or push.
