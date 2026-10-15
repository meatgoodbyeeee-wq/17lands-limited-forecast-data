# Rubric (C12: conditional value of theme-dependent cards)

You are an expert Magic: The Gathering Limited analyst (two-player draft, 40-card decks, 17 lands). Your input file shows ALL cards of one Limited set (names hidden, "~" = the card itself) and then a list of TARGET CARDS. Use only the shown text. Do not use what you may remember about the real set, its archetypes or how cards performed; judge from the cards shown, as if you saw the set for the first time.

Every target card is one whose value depends on other cards (a type or theme to build around, a mechanic, tokens, counters, spells, graveyard, ...). For each target card give three numbers:

- **K (integer 0–12)**: how many OTHER cards of this set (direct or indirect enablers, e.g. members of the type it boosts, token makers of that type, cards that grant the type or keyword) a 40-card deck needs for this card to work as designed. 0 = it works on its own text.
- **ON (0–10)**: the card's Limited grade in a deck that has K such enablers.
- **OFF (0–10)**: the card's Limited grade in a deck that has none of them (its stand-alone value; a dead or nearly dead card is 0–2).

Grade scale (same for ON and OFF): 0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good playable · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb. Use the whole scale; most cards are 3–6. If the card has no real condition, K = 0 and ON = OFF.

Do NOT estimate how likely the deck is to have the enablers: that is computed separately from the set list. Judge the two cases only.

Output exactly one line per target card, in the order of the TARGET CARDS list:
`<id> | <K> | <ON> | <OFF>`
ON and OFF may have one decimal. Example: `1234 | 6 | 8.5 | 2`
Ids are the numbers after `#`. No other text in the file. Every target card must get a line.
