# Rubric (C9: how strong is the card — power broken into questions)

You judge Magic: The Gathering cards for two-player Limited (draft, 40-card decks, 17 lands, opponents with typical draft decks). For each card answer seven questions about HOW STRONG it is, not what it does. Use only the shown text, mana value, colours, type and P/T. "~" is the card itself. Do not use what you may remember about the card or its set; judge the text as if you saw it for the first time.

Think like a strong drafter evaluating a card for the main deck of a deck in its colours.

Output exactly one line per card, in input order:
`<id> <IMP> <UNA> <VAL> <FLOOR> <FLEX> <PLAY> <GRADE>`
Example: `417 3 2 2 2 1 3 6`
Ids are the numbers after `#`. Every card must get a line. No other text in the file.

## The questions
- IMP (0–4) Immediate impact: cast on curve (on the turn its mana value allows), how much does it change the board or the game right away? 0 nothing · 1 small · 2 a fair play for its cost · 3 strong swing · 4 dominates the board on arrival.
- UNA (0–4) Unanswered: if the opponent cannot deal with it (or, for an instant/sorcery, after it resolves), how much has it changed the game two turns later? 0 nothing more · 1 small extra · 2 steady advantage · 3 large advantage · 4 usually wins the game by itself.
- VAL (0–4) Card value: how many cards' worth does it give on average? 0 less than one card (weak or situational) · 1 about one card · 2 about one and a half · 3 about two cards · 4 three or more.
- FLOOR (0–4) Worst realistic case: how useful is it when the situation is bad for it (behind on board, wrong timing, opponent's best answer)? 0 dead card · 1 rarely useful · 2 usually something · 3 almost always useful · 4 always good.
- FLEX (0–3) Flexibility: does it work early and late, on offence and defence, in many board states? 0 narrow · 1 some · 2 broad · 3 very broad (modal, scalable, or good in any position).
- PLAY (0–4) Playability: how often would a good drafter in its colours put it in the main deck? 0 never · 1 only in special decks · 2 filler · 3 usually · 4 always, first picks.
- GRADE (0–10) Overall Limited grade: 0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good playable · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb.

Rules: answer every question for every card (lands and odd cards included: judge what they contribute to a Limited deck). Use the whole scale; most commons are 3–6 in GRADE. When unsure, take the middle value. Do not add explanations.
