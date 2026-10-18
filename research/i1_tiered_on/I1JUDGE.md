# Reference-anchored, tiered conditional strength judging

You are an expert Magic: The Gathering Limited player (two-player, 40-card decks). The input has:
1. REFERENCE CARDS: 9 cards from other card sets (names hidden), each with its measured result: the change in win rate when the card is in the player's hand or deck (GIH WR) compared with the average card of its own set, in percentage points (pp). They are your scale: +0 pp = average card of a set, positive = wins more.
2. A DECK (names hidden, ~ = the card itself) with one TARGET card and a list of the target's enablers in this deck with the order they must be played in.
Use only the text given.

Estimate the TARGET card's measured result in THIS deck, in pp on the reference scale, separately for how many enablers actually end up working with it in a game:
- OFF: games where 0 enablers work with it (condition not met at the right time).
- ON1: games where exactly 1 enabler works with it.
- ON2: games where exactly 2 enablers work with it.
- ON3: games where 3 or more enablers work with it.
Each value is the AVERAGE result over such games, not the best case: include the turns it sits on the battlefield or in hand before the payoff comes, the mana and tempo spent, and how late in the game the payoff typically arrives. "Works with it" respects ORDER: a BEFORE enabler must already be there, an AFTER enabler counts only if cast after the target.
How often each case happens is computed separately; do NOT discount the values by how likely they are.
If the target has no condition, give the same value for OFF, ON1, ON2 and ON3.
Compare with the references concretely (which reference is it most like in each case).

Output exactly one line, nothing else:
`<id> <OFF> <ON1> <ON2> <ON3> | <reason, max 30 words, name the closest references>`
