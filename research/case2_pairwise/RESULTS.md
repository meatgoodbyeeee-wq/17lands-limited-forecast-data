# Case 2 results: blind in-set rankings → Bradley–Terry

Research only. Pages unchanged. FIN and MH3 not used. No 17Lands API calls.
Reproduce: `python3 research/case2_pairwise/case2_eval.py` (outputs `result.json`, `bt_scores.csv`, `fra_frozen.csv`).

## What was done
- 285 groups ranked blind (card name → `~`, rarity/set hidden). 6 duplicate groups from the merge bug were ignored (`groups_fix.json`), so 279 groups were used: HOB 69, MSH 102, FRA 108.
- Replicate consistency (BT from each of the 3 shuffles alone): Spearman 0.70–0.79 in every set. The rankings are stable. The problem is what they measure, not noise.
- Known blinding leak: some rules text names the card or character (for example "The Incredible Hulk" or "Óin"). All three sets are after the knowledge cutoff, so this leaks no results.

## Rule P (pre-registered): **not supported**
The criterion is the mean over HOB and MSH, with w = 0.3.

| | MAE (pp) | Spearman |
|---|---|---|
| pred (case 6 forward) | 2.481 | 0.530 |
| adjusted, w = 0.3 | 2.540 | 0.502 |

The adjustment made both sets worse on both measures. BT alone gives Spearman 0.241 on HOB and 0.326 on MSH. Sensitivity: w = 0.15 is about neutral, and w = 0.5 and 1.0 are worse.

## Why: the rankings are a pick order, not a GIH WR order
The gap is BT z minus actual z, within set, over HOB and MSH:
- **Lands: −1.82.** I put them at the bottom of every group, but their GIH WR is about average.
- **By mana value:** MV 1 −0.66, MV 2 −0.46, MV 3 +0.40, MV 4 +0.55, MV 5 +0.72, MV 6+ ≈ +0.9.

So the rankings rate "what I would pick first", which favours expensive, powerful cards. GIH WR rewards cheap cards and lands that are never dead draws.

## Case 2b (exploratory, added after Rule P failed)
Remove the part of BT z explained by mana value (capped at 7) and "is a land", within set. This uses only card attributes, never 17Lands numbers. Then combine as before.

| | HOB MAE / ρ | MSH MAE / ρ |
|---|---|---|
| pred | 2.489 / 0.506 | 2.473 / 0.554 |
| 2b, w = 0.3 | 2.419 / 0.571 | 2.393 / 0.591 |
| 2b, w = 0.15 / 0.5 | 2.434 / 0.546 · 2.443 / 0.573 | 2.421 / 0.578 · 2.401 / 0.581 |
| 2b BT alone ρ | 0.407 | 0.472 |

This is a clear improvement in both sets and at every w from 0.15 to 0.5. However, the correction was found by looking at HOB and MSH results, so those two sets cannot confirm it.

## FRA: frozen before any FRA 17Lands data (Card Data opens 2026-10-13)
`fra_frozen.csv` holds the production prediction (`gih-c3-28set-20260929`), BT z, BT z 2b, and the adjusted predictions at every w.
SHA-256 at freeze: `9d1d0e692764f91f353913b775647cceb4db881c389a5e8f19f9cfdfd65d309b`.

**Rule P-FRA (pre-registered now, for case 2b):** 2b at w = 0.3 is supported if, on FRA 28-day Public Game Data (cards with ≥ 500 GIH games), it improves **both** MAE and Spearman over the production prediction. Plain case 2 (w = 0.3) is scored the same way, for reference.
Any site change is the user's decision after that check.
