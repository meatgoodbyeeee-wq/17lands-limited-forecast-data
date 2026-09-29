# FIN final holdout check: results (2026-09-29)

Plan and rule: `PLAN.md` (commit c10e073). It was committed before any FIN data was fetched.
The scoring code has not changed since then. There were no 17Lands API calls, and Pages is unchanged.

## Order actually followed
1. c10e073: plan and locked code.
2. a5ea4cd: FIN card texts and features from Scryfall only (Actions run 36561112908).
3. 446ae13: blind C3 extraction for FIN.
   - 312 texts: 302 extracted blind in 3 batches with the unchanged rubric, 4 reused from case 1/6, 6 filled by script.
   - A dry run with synthetic outcomes passed.
4. 20766dd → 09fed39: **one run** in Actions (run 36562141368) that downloaded, aggregated and scored FIN. Results were committed by the bot.

## FIN data
- Premier Draft, 2025-06-10 → 2025-07-08, 686,290 games (file sha256 `f6452e62…a6a6`). 345 cards have ≥ 500 GIH games.
- 295 cards scored: 263 matched by exact name and 32 by front face.
  The 50 unmatched cards are special-guest reprints (e.g. Lightning Bolt, Counterspell) that are not in Scryfall's FIN set. They are excluded, as the bonus sheets were in case 6.

## Result (3-seed mean; seed-to-seed range in brackets)

| arm | training | features | MAE (pp) | Spearman | bias (pp) | tail bias sum | strong/weak recall |
|---|---|---|---|---|---|---|---|
| **P** current model | 21 sets | baseline | 2.611 [0.008] | 0.407 [0.005] | −0.21 | 9.80 | 0.289 |
| **F** final candidate | 21 + 7 sets | baseline + C3 | **2.425** [0.008] | **0.514** [0.001] | +0.20 | **8.59** | **0.367** |
| P28 (decomposition) | 21 + 7 | baseline | 2.549 | 0.424 | +0.11 | 9.48 | 0.300 |
| C21 (decomposition) | 21 | baseline + C3 | 2.465 | 0.490 | −0.10 | 8.93 | 0.361 |

**Rule F: confirmed.** F lowers MAE by 0.187pp and raises Spearman by 0.106.
- Paired bootstrap over FIN cards (2,000 resamples, 90% interval, descriptive):
  - MAE difference: −0.27 to −0.10pp
  - Spearman difference: +0.07 to +0.15
  - F is better in 100% of resamples on both.
- MAE by rarity (P → F, seed-averaged): common 1.88 → 1.71, uncommon 2.44 → 2.23, rare 3.64 → 3.48, mythic 3.32 → 3.10.
- Tails: top-10% bias improves from −4.23 to −3.13pp. Bottom-10% bias barely moves (+5.57 → +5.46).
- Decomposition:
  - C3 alone (C21): −0.146pp and +0.082. This is most of the gain.
  - The newer training sets alone (P28): −0.062pp and +0.016.
  - Together (F), the gain is larger than either part.
- The independent recomputation from `fin_predictions.csv.gz` reproduces the table.

## Caveats
- One set. The FIN gains are larger than the 21-set backtest's (C3: −0.10pp / +0.045), so FIN may be a favourable draw for C3.
- FIN predates the extractor's cutoff, so C3 carries the leakage caveat here too. The post-cutoff evidence remains MSH/HOB (case 6).
- F trains on sets released after FIN. C21 has no such issue and still passes on its own.
- The FIN C3 codes run higher than earlier sets:
  - cards 0.29 vs about 0.10–0.20
  - repeat 0.46 vs 0.16–0.33
  - drawback 0.17 vs 0.06–0.12

  Part of this is set content: FIN has many legendary creatures, Saga creatures and Towns. Part may be extractor drift. It was not adjusted, since the extraction was frozen before the outcome.
- FIN is no longer a holdout.

## What this means
The final candidate (training on the 21 research sets and the 7 newer sets, with C3) beat the current model on the untouched FIN set, as required.
Adopting it at the next production retrain is the user's decision. Production would need C3 extraction for each new set before release.
