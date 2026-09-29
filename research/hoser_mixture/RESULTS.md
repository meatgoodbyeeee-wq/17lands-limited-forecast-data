# Colour-hoser mixture adjustment: results (2026-09-29)

Plan: `PLAN.md` (commit 6227339), committed before any counterfactual prediction.
Outputs: `result.json`, `cards.csv` and `fra_frozen.csv`. Pages is unchanged.

## Backtest (15 historical hosers; models trained without the card's set)

| | MAE (pp) | mean error (pp) |
|---|---|---|
| current prediction | **2.413** | +1.06 |
| mixture adjusted | 2.507 | +0.99 |
| live version only | 2.733 | |
| dead version only | 2.541 | |

- Set-level MAE improves in 0 of 3 sets.
- Within-set metrics of AFR, SNC and MOM with the adjusted cards swapped in: MAE 2.466 → 2.468pp, Spearman 0.589 → 0.588.

**Rule H: fail.** The mixture adjustment for the bonus type is not adopted.

## Why it fails
- **The model barely separates the live and dead versions.**
  - Its mean predicted live − dead gap is 0.58pp.
  - The observed gap is 3.35pp raw and 5.42pp as a difference-in-differences.
  - Some gaps point the wrong way: Knockout Blow at mana value 1 is predicted below Knockout Blow at mana value 3.
  - Mixing two model predictions therefore changes little, and not reliably in the right direction.
- **The errors follow maindeck rate** (`research/hoser_metrics`):
  - The five hosers players rarely maindecked (≤ 0.4× the rate of peer uncommons: Divine Smite, Change the Equation, Glistening Deluge, Lithomantic Barrage, Surge of Salvation) are over-predicted by **+3.7pp** on average.
  - The other ten are close to their actual values (−0.3pp).
  - The rarely maindecked five are the cards that are weak when the colour does not match.

## FRA (only type): frozen, not backtestable
s = 0.7 and blank = set predicted mean − 8.61pp. These values have not been validated; they are kept for comparison with the FRA Public Game Data.

| card | published | adjusted |
|---|---|---|
| Flourishing Grapple | 56.68 | 53.83 |
| Terminal Criticism | 56.51 | 54.36 |
| Refute Destiny | 56.31 | 54.11 |
| Essence Burn | 54.74 | 54.48 |
| Precise Redaction | 54.04 | 51.77 |

## Implication
The model's own counterfactual predictions cannot price colour conditions.
A workable adjustment would have to come from an explicit, pre-release judgement of how weak the card is when the colour does not match, calibrated on observed data, rather than from edited-text predictions.
