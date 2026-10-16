# Deck building task (forced card)

You are a strong Magic: The Gathering Limited player. The input file names one FORCED CARD and then a sealed pool (names hidden, ~ = the card itself). Your deck MUST include the forced card. Build the best 40-card deck around it from this pool, as you would to win: choose its colours and pick the other cards to make the forced card as effective as possible while keeping the deck strong overall (normally 23 non-land cards incl. the forced card, 17 lands). Judge from the text only; do not use memory of real cards.

Output exactly two lines and nothing else:
`MAIN: #id #id ...` (every non-basic card you play, including the forced card)
`BASICS: <W> <U> <B> <R> <G>`
