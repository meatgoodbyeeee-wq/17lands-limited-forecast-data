# Synergy judging task

The input gives a 40-card Limited deck (names hidden, "~" = the card itself) and a list of TARGET cards in that deck. For each target card, look only at the other cards in THIS deck and answer:
- N: how many other cards in this deck enable or feed its condition (cards it needs, rewards, counts, or that supply what it needs — e.g. members of the type it boosts, token makers of that type, spells it triggers on).
- SCORE (0–10): how fully its condition is met in this deck. 0 = never works here · 3 = sometimes · 5 = about half of games · 8 = most games · 10 = always.

Output one line per target card, in the order given, nothing else:
`<id> <N> <SCORE>`
