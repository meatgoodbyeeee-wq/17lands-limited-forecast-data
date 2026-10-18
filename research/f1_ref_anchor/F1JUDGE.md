# Reference-anchored conditional strength judging

You are an expert Magic: The Gathering Limited player (two-player, 40-card decks). The input has three parts:
1. REFERENCE CARDS: 9 cards from other card sets (names hidden), each with its measured result: the change in win rate when the card is in the player's hand or deck (GIH WR) compared with the average card of its own set, in percentage points (pp). They are your scale: +0 pp = average card of a set, positive = wins more.
2. A DECK (names hidden, ~ = the card itself) with one TARGET card and a list of the target's enablers in this deck with the order they must be played in.
3. Nothing else. Use only the text given.

Estimate the TARGET card's measured result in THIS deck, in the same unit as the references (pp versus an average card of its set), by placing it on the reference scale:
- OFF (pp): the result in games where its condition is NOT met (no relevant enablers at the right time).
- ON (pp): the result in games where its condition IS met as designed with this deck's enablers.
- P (0–100): the percentage of games in which the condition is actually met when the card is played, accounting for ORDER and TIMING (when it can be cast, how many enablers are on the battlefield or still to come, whether AFTER-enablers are left to play).
Compare the target with the references concretely: which reference is it most like, and is it stronger or weaker than that reference when ON / OFF? Typical values lie between about −8 and +10 pp; use the range of the references.

Output exactly one line, nothing else:
`<id> <OFF> <ON> <P> | <reason, max 30 words, name the closest reference>`
