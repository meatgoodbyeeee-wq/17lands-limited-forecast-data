# Deck colour step 1: 28-set pair win rates and ceilings (pre-registered measurement plan)

Research only; Pages unchanged. FIN, MH3, FRA refused. No 17Lands API calls (official Public Game Data via GitHub Actions only).
Written before any aggregate exists. This step decides nothing about production; it measures what a better deck colour model could be worth.

## Data (`scripts/deck_pair_aggregate.py`, workflow `deck_pair_data.yml`)
Same window as case 6 (earliest draft_time + 28 days, Premier Draft), the 28 training sets.
- Per game: `main_colors` (normalised to WUBRG order), splash present or not, won, and a fixed hash half of draft_id.
- `{SET}_pairs.csv`: games and wins by deck colour group (main colours × splash) and by half.
- `{SET}_cardpair.csv`: per card, GIH games and wins (same card logic as case 6) by deck group: the 10 two-colour pairs (splash allowed) plus `other`.
"Pair WR" = unsplashed two-colour decks, as on the 17Lands colour ratings page.

## Measurements
- **M1** Pair WR table for 28 sets; within-set SD of the 10 pair WRs versus sampling noise; split-half Spearman of pair WR (how stable the 10-pair order is at all).
- **M2** Current deck colour formula (mean GIH of commons/uncommons whose colours fit the pair) backtested on 28 sets, within-set Spearman with pair WR, averaged over sets:
  (a) with the production 28-set OOF card predictions (honest);
  (b) with actual card GIH (oracle cards; shows the formula's own ceiling).
- **M3** Ceiling for card GIH if pair WRs were known. Deck baseline per card b = Σ shares × (pair WR − set mean pair WR):
  (A) shares = the card's actual GIH games by pair (upper bound);
  (B) shares = equal over the pairs the card's colours fit (colourless: all 10) — what a perfect pair forecast could give before release.
  Adjusted = pred + λ·b, λ fitted on the other 27 sets (OLS of OOF residual on b). Report pooled MAE and mean within-set Spearman versus pred.

## What follows
If M3(B) shows a gain worth having (rule of thumb: ≥ 0.10pp MAE), step 2 (a new deck colour model) is pre-registered separately with M2(a) as its baseline. Otherwise card GIH work should not wait on deck colours.
