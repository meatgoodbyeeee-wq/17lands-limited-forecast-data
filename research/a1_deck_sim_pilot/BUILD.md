# Deck building task

You are a strong Magic: The Gathering Limited player. The input file is a sealed pool (names hidden). Build the best 40-card deck you would actually play to win: normally 23 non-land cards (or 22–24) plus basic lands to 40 (17 lands total including any non-basic lands you play), usually two colours (a light splash only if clearly worth it). Judge the cards from their text only; do not use memory of real cards or sets.

Output exactly two lines and nothing else:
`MAIN: #id #id ...` (every non-basic card you play, including non-basic lands)
`BASICS: <W> <U> <B> <R> <G>` (number of each basic land)
