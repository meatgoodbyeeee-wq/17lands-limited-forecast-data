# Rubric (C12: power when the card's enablers are present vs absent)

You are an expert Magic: The Gathering Limited analyst (two-player draft, 40-card decks, 17 lands). Your input file shows ALL cards of one Limited set (names hidden, "~" = the card itself) and then a list of TARGET CARDS. Use only the shown text. Do not use what you may remember about the real set, its archetypes or how cards performed; judge from the cards shown, as if you saw the set for the first time.

Every target card is one whose value depends on other cards (a type or theme to build around, a mechanic, tokens, spells, counters, graveyard, ...). For each target card answer four things:

1. **E (enablers)**: every card of the list that makes the target card work: cards it needs, rewards or counts (direct) and cards that supply those things without being them (token makers, type or keyword granters, tutors, recursion, sacrifice/flicker/copy engines, cost reducers; indirect, e.g. for a Hero lord: Hero cards and cards that create Hero tokens). Never list the target card itself.
2. **K**: the number of enablers (from E, castable in the deck) a deck needs to contain for the target card to be reliably "online" (0–8). K = 0 if the card works without any support.
3. **ON** (0–10): the card's strength in the main deck of a deck in its colours when it IS online (K enablers present).
4. **OFF** (0–10): the card's strength in the main deck when it is NOT online (fewer than K enablers): what it is worth on its own text, with at most incidental support.

Scale for ON and OFF: 0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good playable · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb. ON must be at least OFF. Judge ON and OFF independently of how many enablers the set has: how often the card is online is computed separately from your E list, so do NOT discount ON for thin support. Use the whole scale.

Output exactly one line per target card, in the order of the TARGET CARDS list:
`<id> | <K> | <ON> | <OFF> | E: <entries or ->`
Entries are separated by spaces. An entry is either `#<id>` (a single card of the list) or `T:<Subtype>` (every card of the list whose type line has that subtype, e.g. `T:Hero`, `T:Zombie`, `T:Equipment`; use it instead of listing many cards of one type). At most 40 entries. K is an integer 0–8; ON and OFF are numbers with at most one decimal. Example:
`1234 | 3 | 9 | 5 | E: T:Hero #2201 #2290 #3117`
Ids are the numbers after `#`. No other text in the file. Every target card must get a line.
