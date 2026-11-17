# Colour-pair card GIH — exploratory step 1 (2026-11-17)

**Exploratory, not pre-registered. Decides nothing.** Pages and production unchanged.

Target: a card's GIH WR in decks whose main colours are one of the 10 pairs (splash allowed), first 28 days, Premier Draft, all users
(`research/deck_pair/data/{SET}_cardpair.csv.gz`). Cells with ≥ 500 GIH games. 26 sets (KHM, STX have no deck colours).
**FRA was aggregated (2026-11-17) but is kept out of this exploration** so it can be a held-out set.

Reproduce (inputs: `research/g3_retrain/oof_B11g.csv.gz` from research/q-small-gains; card colours from `export_gih_c3_28set.training()`;
`research/d9_colour_strength/pair_table.csv` from main):
```
python3 research/pair_gih/build.py oof_B11g.csv.gz colors.csv cells.csv.gz
python3 research/pair_gih/explore.py cells.csv.gz research/pair_gih/explore.json pair_table.csv
```

## E1: what the spread of cell GIH is made of (within set, SD in pp, mean over 26 sets)
25,046 cells, 6,807 cards, 3.6 cells per card.

| part | SD (pp) |
|---|---|
| total | 3.92 |
| card (overall strength) | 3.35 |
| pair (deck colour strength) | 1.45 |
| card × pair interaction, noise removed | 1.25 |
| sampling noise | 1.16 |

Within one card, its pairs differ by SD 1.86pp (1.58pp after removing noise).

## E2: simple forecasts of cell GIH (23,361 cells with a B11g prediction)
| forecast | MAE (pp) | within-set Spearman | within-card corr |
|---|---|---|---|
| H0: B11g overall prediction for every pair | 2.487 | 0.539 | 0.00 |
| H0r: H0 + offset by colour relation | 2.482 | 0.542 | 0.12 |
| H1p: H0 + λ·D9 pair forecast (D_B5, λ 0.38) | 2.457 | 0.553 | 0.23 |
| **H2p: H1p + offset by colour relation (realistic best)** | **2.452** | **0.556** | **0.26** |
| H1: H0 + λ·actual pair WR (oracle pair, λ 0.59) | 2.287 | 0.637 | 0.54 |
| H2: H1 + offset by colour relation | 2.254 | 0.641 | 0.56 |
| O0: actual overall GIH for every pair (oracle card) | 1.562 | 0.817 | 0.00 |
| O1: O0 + λ·actual pair WR | 1.394 | 0.860 | 0.54 |
| O2: in-sample card + pair fit (ceiling for additive) | 1.132 | 0.899 | 0.61 |
| noise floor | 0.811 | | |

λ and offsets are fitted leave-one-set-out. H2p beats H0 in 18/26 sets.

## E3: where the interaction lives (residual of the additive fit, by card colour vs pair)
- Gold card in exactly its pair: +0.37pp above additive (26/26 sets). In a pair with only one of its colours: −2.0pp (0/25).
- Mono-colour card splashed into a pair without its colour: −1.4pp (3/24 sets).
- Against H1, a gold card in its exact pair is under-forecast by 1.6pp; the relation offset fixes most of it (gold-exact MAE 2.68 → 2.31).

## Reading
1. Cell error is dominated by the card's overall forecast (overall MAE 2.15pp). Perfect overall GIH alone would cut the cell MAE from 2.49 to 1.56.
2. The pair-specific part is real (interaction SD 1.25pp, within-card 1.58pp), but the main lever, deck colour strength, is hard to forecast before release (D9: best Spearman 0.46). With the D9 forecast the gain is 0.03pp; with the actual pair WR it would be 0.20pp.
3. Colour relation (gold in its own pair, splash penalty) is a cheap, stable rule; it matters for gold and splashed cells, little on average.
