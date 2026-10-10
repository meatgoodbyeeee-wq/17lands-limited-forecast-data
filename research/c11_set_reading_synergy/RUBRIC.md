# Rubric (C11: card judged against the whole set list)

You are an expert Magic: The Gathering Limited analyst (two-player draft, 40-card decks, 17 lands). Your input file shows ALL cards of one Limited set (names hidden, "~" = the card itself) and then a list of TARGET CARDS. Use only the shown text. Do not use what you may remember about the real set, its archetypes or how cards performed; judge from the cards shown, as if you saw the set for the first time.

Every target card is one whose value depends on other cards (a type or theme to build around, a mechanic, a counter or graveyard plan, tokens, spells, ...). For each target card decide:

1. **D (direct enablers)**: cards in the list that the target card needs, rewards or counts: members of a creature type it names, cards with a keyword/counter/artifact/graveyard/spell/etc. role that its text checks or boosts.
2. **I (indirect enablers)**: cards that supply the D things without being them: token makers of that type, cards that grant the type or keyword, tutors/recursion that fetch them, sacrifice or flicker engines that feed the effect, cost reducers, copy effects, and so on. Think through what the target card actually does and which other cards in the set make it work, even through a second step (for a Hero lord: Hero cards are D; cards that create Hero tokens are I).
   Never list the target card itself.
3. **EXP**: the expected number of enablers (D plus I) that a typical well-built 40-card deck in the target card's colours (plus its most likely partner colour) will actually contain. Use the freq values: freq is the expected number of copies of that card a drafter sees in 3 packs, so common cards are abundant and rare/mythic cards are seen only occasionally; a theme made of rares is thin, a theme made of commons and uncommons is deep. Count only enablers that can be cast in that deck (shared colour, or colourless).
4. **PAY (0–10)**: how strong the target card is in the main deck of a deck in its colours in THIS set, given the enablers that exist and how likely a drafter is to have them: 0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb. A theme-dependent card is a bomb only if the enablers are deep enough in the set; it is weak if they are missing or thin; it may still be good on its own text.

Output exactly one line per target card, in the order of the TARGET CARDS list:
`<id> | <PAY> | <EXP> | D: <entries or -> | I: <entries or ->`
Entries are separated by spaces. An entry is either `#<id>` (a single card of the list) or `T:<Subtype>` (every card of the list whose type line has that subtype, e.g. `T:Hero`, `T:Zombie`, `T:Equipment`; use it instead of listing many cards of one type). At most 40 entries per list. Example:
`1234 | 7 | 5.5 | D: T:Hero | I: #2201 #2290 #3117`
Ids are the numbers after `#`. No other text in the file. Every target card must get a line. EXP is a number with at most one decimal (0–15).
