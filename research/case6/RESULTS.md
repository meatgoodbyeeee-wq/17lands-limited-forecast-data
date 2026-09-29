# Case 6: results (2026-09-29)

Plan and decision rules: `PLAN.md`, committed before any new-set or top-player outcome was aggregated.
FIN (final holdout), MH3 (excluded) and FRA (live) were not used. No 17Lands API calls were made. Pages is unchanged.

## Data
- 17Lands public game data for the 21 research sets and 7 new sets (EOE, TLA, ECL, TMT, SOS, MSH, HOB). It was read and aggregated in GitHub Actions (`case6_data.yml`).
- Check: the `all` group reproduces the stored `compact_28d` games and wins exactly for all 5,344 research rows (`check.json`).
- New-set features were built from Scryfall with `card_features` unchanged. The following were dropped because Scryfall has no in-set card for them:
  - bonus-sheet reprints: 29 in EOE and 51 in SOS
  - 1 card in ECL and 2 in TMT
  Front-face fallback matched 72 double-faced cards. The unmatched list in the report is capped at 40 names; the SOS count is 320 − 269.
- HOB: the window runs from 2026-08-11, but the file ends on 2026-08-29, so it covers about 18 days.
  MSH (released 2026-06-26) has a full 28-day window.
- The C3 extraction for the new sets was committed (a971687) before any new-set outcome was read.
  - Of 1,689 unique card texts, 1,640 were read blind in 11 batches with the unchanged `RUBRIC.md`.
  - 48 texts were reused from case 1 by signature, and 6 with no rules text were filled by script.

## Part A: add newer sets to training (forward, arm A = 21 research sets, arm B = 21 + earlier new sets)

| 3-seed mean over TLA–HOB | A | B | change |
|---|---|---|---|
| within-set MAE (pp) | 2.6941 [seed range 0.0014] | **2.6546** | −0.040 |
| within-set Spearman | 0.4572 | **0.4627** | +0.006 |
| bias (pp) | −0.85 | −0.74 | +0.11 |
| tail bias sum (pp) | 9.868 | 9.840 | −0.028 |

Per set (seed 20260922):

| set | MAE change (pp) | Spearman change |
|---|---|---|
| TLA | +0.002 | −0.007 |
| ECL | −0.002 | −0.003 |
| TMT | −0.044 | −0.007 |
| SOS | −0.038 | +0.012 |
| MSH | −0.096 | +0.047 |
| HOB | −0.053 | −0.017 |

**Rule A: PASS (4/4).** MAE improves, Spearman does not fall, B wins in 5/6 sets, and the gain is about 30× arm A's seed range.
Reading: most of the gain is a level correction (the negative bias shrinks). Ranking barely changes (+0.006), and only MSH ranks clearly better.
Under the plan, the extended training set is used at the next production retrain. That retrain needs the user's decision.

## Part B: C3 on the new sets (post-cutoff leakage check for proposal 1)

3-seed means, B (extended training, baseline features) vs B + C3:

| set | n | B MAE | B+C3 MAE | B Spearman | B+C3 Spearman |
|---|---|---|---|---|---|
| MSH (clean) | 278 | 2.585 | **2.473** | 0.533 | **0.553** |
| HOB (clean) | 184 | 2.668 | **2.489** | 0.385 | **0.505** |
| **MSH+HOB mean** | | 2.6265 | **2.4812** | 0.4590 | **0.5289** |
| EOE | 262 | 2.374 | 2.197 | 0.476 | 0.573 |
| TLA | 282 | 2.506 | 2.360 | 0.482 | 0.533 |
| ECL | 268 | 2.477 | 2.461 | 0.560 | 0.564 |
| TMT | 188 | 2.969 | 2.902 | 0.474 | 0.467 |
| SOS | 269 | 2.722 | 2.694 | 0.343 | 0.390 |

**Rule B: PASS.** On the two sets played after the extractor's knowledge ends, C3 improves both MAE (−0.145pp) and Spearman (+0.070). This is larger than the 21-set backtest's −0.100pp / +0.045.
The pre-cutoff new sets (EOE–SOS; same leakage caveat as the backtest) also improve on MAE in 5/5 and on Spearman in 4/5.
Caveats:
- It is 2 sets (462 cards).
- HOB's window is short.
- MSH was released on the cutoff boundary.

FRA (frozen in case 1) remains the next prospective check.

## Part C: top-player GIH WR (`top60n50` = player WR bucket ≥ 0.60 and ≥ 50 games; card needs ≥ 500 such games)

### C1 descriptive (mean over the 16 research sets that have the bucket; new sets in brackets)
- The top group plays 20.0% of games [21.5%]. Its game win rate is 63.6% [64.5%]; this is inflated by selection, because the bucket includes the same games.
- Top-group GIH minus overall GIH: +8.3pp [+8.6pp]. The SD across cards is 2.99pp for top vs 3.44pp overall.
- Within-set Spearman(top, overall): 0.934 [0.912].
- Split-half reliability: top 0.896 [0.853], non-top 0.981 [0.970].
  The correlation between top and non-top corrected for that unreliability is 0.991 [0.983].
- **Reading:** top players and everyone else rank cards almost identically. The top-player target differs mainly because it is noisier (fewer games), sits at a higher level, and is compressed.
- Sensitivity: within-set Spearman vs the primary target is 0.965 for `top56n50`, 0.906 for `top64n50` and 0.987 for `top60`.

### C2 modelling (LOSO over the 16 sets, 3,849 cards, 3 seeds, scored against top-player GIH)

| arm | MAE (pp) | Spearman | bias (pp) | tail bias sum | pred/actual SD |
|---|---|---|---|---|---|
| T0: overall model + mean shift | 1.931 [range 0.0006] | 0.515 | −0.48 | **6.52** | 0.67 |
| T1: trained on top GIH | 1.823 | 0.543 | +0.02 | 6.92 | 0.58 |
| T0 + C3 | 1.882 | 0.545 | −0.44 | **6.08** | — |
| T1 + C3 | **1.788** | **0.569** | +0.02 | 6.76 | — |

**Rule C: PASS.** T1 beats T0 on MAE (−0.108) and Spearman (+0.028), and wins MAE in 13/16 sets (9 required). It also wins Spearman in 12/16.
With C3, T1 + C3 beats T1 on both MAE and Spearman in 15/16 sets.
Caveats:
- T1 learns from fewer rows than T0: 15 sets, and only cards with ≥ 500 top games. T0 learns from all 20 other sets. The comparison therefore does not favour T1.
- Part of T1's MAE gain is calibration: level (T0 bias −0.48) and scale (T0 is over-dispersed for the compressed target).
  T1 is worse on the tails: its tail bias sum is 6.92 vs 6.52.
- The target excludes cards with < 500 top games (about 10% of cards), so low-play cards are not evaluated.
- For scale: on the same cards, T0 ranks overall GIH at Spearman 0.528, compared with 0.515 against top GIH. The top target is only slightly harder to rank.

### Forward check on TLA–HOB (reported only; trained on the research sets plus earlier new sets; the 3 seeds are averaged into one prediction)

| arm | MAE | Spearman | bias |
|---|---|---|---|
| T0 | 2.310 | 0.456 | −1.41 |
| T1 | 2.079 | 0.518 | −0.97 |
| T0 + C3 | 2.255 | 0.479 | −1.38 |
| **T1 + C3** | **2.037** | **0.545** | −0.98 |

T1 + C3 is best in every new set on MAE and Spearman. HOB, the one set fully after the cutoff, has MAE 1.81 and Spearman 0.600.
All arms under-predict the level of the new sets by about 1pp. The top group's advantage grows in newer sets (+8.6pp vs +8.3pp), so a level correction will be needed.

## Summary
1. **Extended training (Part A):** passes, but it is a small, mostly level gain. Use it at the next retrain.
2. **C3 (Part B):** confirmed on post-cutoff sets. It is the strongest single improvement found (proposals 5, 1 and 6 combined).
3. **Top-player target (Part C):** rankings are nearly the same as overall GIH. If the site shows a top-player forecast, a dedicated T1 + C3 model is better than shifting the overall forecast. Whether to show it is the user's decision.
4. FIN is still unused. The intended next step is to freeze the final candidate (extended training + C3; T1 + C3 if a top-player forecast is wanted) and score FIN once.

## Files
- `case6_research.py` (`check` / `forward` / `top`), `forward.json`, `forward_oof.csv.gz`, `top.json`, `top_oof.csv.gz`
- `c3_queue.py`, `c3_cards_new.csv.gz`, `c3_raw/n00–n10.txt`, `c3_features_new.csv.gz`
- `data/`: case-6 aggregates, manifests and new-set feature tables. Built by `scripts/case6_aggregate.py` and `scripts/case6_features.py`.
