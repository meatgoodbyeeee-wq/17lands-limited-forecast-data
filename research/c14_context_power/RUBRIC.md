# Rubric (C14: card power judged in the context of its whole set)

You judge Magic: The Gathering cards for two-player Limited (draft, 40-card decks, 17 lands). Your input file shows ALL cards of one Limited set (names hidden, "~" = the card itself), with rarity and freq (expected number of copies of that card a drafter sees in 3 packs: commons are abundant, rares and mythics scarce). Use only the shown cards. Do not use what you may remember about the real set or how cards performed; judge as if you saw this set for the first time.

**Judge every card as it plays in THIS set**: think like a strong drafter who has read the whole set list. Consider which other cards of the set support it (creature types, mechanics, themes, token makers, and how many of them there are given their rarity), what a typical deck in its colours in this set will contain, and what opponents in this set typically do. A card that needs a type or theme is strong if the set supplies that type or theme in depth, and weak if the set supplies it thinly. Judge the card's real expected strength in a typical deck of this set, not in the abstract.

For each card answer seven questions about HOW STRONG it is.

Output exactly one line per card, in the order of the list:
`<id> <IMP> <UNA> <VAL> <FLOOR> <FLEX> <PLAY> <GRADE>`
Example: `417 3 2 2 2 1 3 6`
Ids are the numbers after `#`. Every card must get a line (integers only). No other text in the file.

## The questions
- IMP (0–4) Immediate impact: cast on curve (on the turn its mana value allows) in a typical deck of this set, how much does it change the board or the game right away? 0 nothing · 1 small · 2 a fair play for its cost · 3 strong swing · 4 dominates the board on arrival.
- UNA (0–4) Unanswered: if the opponent cannot deal with it (or, for an instant/sorcery, after it resolves), how much has it changed the game two turns later? 0 nothing more · 1 small extra · 2 steady advantage · 3 large advantage · 4 usually wins the game by itself.
- VAL (0–4) Card value: how many cards' worth does it give on average? 0 less than one card (weak or situational) · 1 about one card · 2 about one and a half · 3 about two cards · 4 three or more.
- FLOOR (0–4) Worst realistic case: how useful is it when the situation is bad for it (behind on board, wrong timing, opponent's best answer)? 0 dead card · 1 rarely useful · 2 usually something · 3 almost always useful · 4 always good.
- FLEX (0–3) Flexibility: does it work early and late, on offence and defence, in many board states? 0 narrow · 1 some · 2 broad · 3 very broad.
- PLAY (0–4) Playability: how often would a good drafter in its colours in this set put it in the main deck? 0 never · 1 only in special decks · 2 filler · 3 usually · 4 always, first picks.
- GRADE (0–10) Overall Limited grade in this set: 0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good playable · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb.

Rules: answer every question for every card (lands and odd cards included). Use the whole scale; most commons are 3–6 in GRADE. When unsure, take the middle value. Do not add explanations.
