# Deck colour step 1 results (measurement; see PLAN.md)

Research only; Pages unchanged. Data: official Public Game Data, 28-day window, via `deck_pair_data.yml`.
**26 sets.** KHM and STX are excluded because their public files have no `main_colors`/`splash_colors` column.
Pair WR = unsplashed two-colour decks.
Reproduce: `python3 research/deck_pair/analyze.py` (outputs `result.json`, `pair_wr.csv`, `formula_backtest.csv`).

## M1: the target is large and stable
- Within-set SD of the 10 pair WRs: **2.45pp** (mean over sets). The sampling SE of a pair WR is only 0.29pp (median).
- Split-half Spearman of the 10-pair order: **0.87**. At 28 days the pair order is real, not noise.

## M2: the current deck colour formula
Metric: within-set Spearman with pair WR, mean over 26 sets.

| | Spearman |
|---|---|
| (a) formula with production OOF card predictions (honest) | **0.35** (per set −0.28 to 0.81) |
| (b) same formula with actual card GIH | 0.62 |

Part of (b) is circular: actual GIH already contains the strength of the decks the card was played in. So 0.62 is an optimistic ceiling for this formula.

## M3: what known pair WRs would give card GIH
Card baseline b = Σ shares × (pair WR − set mean). Adjusted = pred + λ·b, with λ fitted leave-one-set-out.

| | MAE (pp) | mean within-set Spearman | λ |
|---|---|---|---|
| pred | 2.396 | 0.562 | – |
| (A) actual play shares (upper bound) | 2.283 | 0.618 | 0.47 |
| **(B) shares from card colours (perfect pre-release pair forecast)** | **2.312** | **0.597** | 0.55 |

## Reading
- A **perfect** pair forecast would improve card GIH by 0.085pp MAE and +0.035 Spearman. This is just under the plan's 0.10pp rule of thumb. A realistic forecast would capture only part of it.
- The deck colour forecast itself has much more room: honest 0.35 against a stable target (split-half 0.87).
- Better card predictions alone push the same formula towards 0.62.
- So the main payoff of step 2 is the deck colour forecast itself. Card GIH work does not need to wait for it.
