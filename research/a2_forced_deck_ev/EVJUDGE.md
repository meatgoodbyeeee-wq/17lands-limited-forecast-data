# Conditional strength judging task

You are an expert Magic: The Gathering Limited player (two-player, 40-card decks). The input gives a deck (names hidden), one TARGET card in it, and a list of its enablers in this deck with the order they must be played in. Judge the target card in THIS deck:

- OFF (0–10): its Limited grade in a game where its condition is NOT met (no relevant enablers at the right time).
- ON (0–10): its Limited grade in a game where its condition IS met as designed with the enablers of this deck.
- P (0–100): in what percentage of games is the condition actually met when the card is played? Account for ORDER and TIMING: when the target can be cast (mana value, curve), how many enablers are typically on the battlefield or still to come at that point (draws, removal, combat losses), and whether enablers that must come AFTER the target are still left to play. E.g. an expensive card that triggers on spells cast afterwards only gets the spells drawn or held after it lands.

Grade scale for ON and OFF: 0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb. Use the full scale; a bomb when enabled should be 9–10.

Output exactly one line, nothing else:
`<id> <OFF> <ON> <P> | <reason, max 25 words>`
