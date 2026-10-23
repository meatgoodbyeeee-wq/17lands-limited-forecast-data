# Rubric (C9: how strong is the card — power broken into questions)

You judge Magic: The Gathering cards for two-player Limited (draft, 40-card decks, 17 lands, opponents with typical draft decks). For each card answer seven questions about HOW STRONG it is, not what it does. Use only the shown text, mana value, colours, type and P/T, and the SET INFO lines if the card has them. "~" is the card itself. Do not use what you may remember about the card or its set; judge the text as if you saw it for the first time.

Think like a strong drafter evaluating a card for the main deck of a deck in its colours.

## SET INFO (new in this rubric)
Some cards are followed by lines that start with `SET INFO`. A script counted them from the complete card list of the set the card comes from (the set is not named, and you do not know it). They say how common the things are that the card's text refers to (a creature type, a keyword, a card type such as instant or artifact). You cannot know this otherwise. The counts are facts about the set, not an opinion about the card. Cards without SET INFO lines are judged exactly as before.
How to use them:
- Use SET INFO only to decide how often the card's condition is met in a deck that plays the card. The number to reason about is "about E of the 15 creatures" or "of the 23 spells" of an ordinary two-colour deck that can play the card. The "typical deck" numbers are weighted by how often each card is seen in packs (rares and mythics count less than commons and uncommons), which is why they can differ from the plain card counts; use the typical-deck number. A line marked "best case" describes a deck built around the theme; an ordinary deck has fewer.
- As a guide: if a typical deck has about 5 or more of 15 creatures (or 7 or more of 23 spells) that the card refers to, the condition is usually met and you should judge the card as the text reads when it works. About 2 to 4 creatures (3 to 6 spells): it works part of the time, so judge it between its working and not-working strength. Under 2 creatures (under 3 spells): it is mostly inactive and its value comes from the rest of its text. Count the card's other uses too: a card that is fine without the condition stays fine.
- SET INFO can lower a grade as well as raise it. Do not raise a grade because SET INFO exists. Raise it only if the information shows that the condition the text depends on is common, and lower it (or keep it low) if the condition is rare.
- Sequencing still counts (for example a permanent that must be on the battlefield before you cast the spells it rewards), and so does the cost of building around the card. When the information does not change what you think of the card, keep your usual answer.
- "also make such tokens" (printed only when at least 3 other cards do) counts other cards that create a token of the same kind. They help only if the card in front of you can use those tokens.

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
