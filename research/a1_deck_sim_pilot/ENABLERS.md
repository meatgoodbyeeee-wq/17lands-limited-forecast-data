# Enabler listing task (factual)

Input: a 40-card Limited deck (names hidden, ~ = the card itself) and one TARGET card. List the cards in this deck that make the target card's condition work, and the ORDER they must be played in relative to the target.

Output, nothing else:
`TARGET <id> MV <mv>`
then one line per enabler: `<id> MV <mv> <BEFORE|AFTER|EITHER> <short reason, max 8 words>`
BEFORE = must already be on the battlefield / in graveyard when the target is cast or acts; AFTER = only counts if played after the target is on the battlefield (e.g. spells cast after an enchantment that triggers on casting); EITHER = works in both orders.
If the target has no condition, output only the TARGET line.
