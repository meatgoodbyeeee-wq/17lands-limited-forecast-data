# FIN final holdout check for the GIH WR model

This is research only. Pages does not change and no 17Lands API calls are made. The FIN outcome comes from the official S3 Public Game Data file.
This plan and the scoring code (`fin_final.py`) are committed before any FIN data is fetched.

## Why
FIN was held out from all GIH research: every GIH script in this repo refuses it.
Since then, choices were made on the 21 research sets (the model in case 5, C3 in case 1) and on the 7 newer sets (case 6).
This is the one-time check that the final candidate still beats the current model on a set that played no part in any of those choices.

## Arms (locked)
Every arm uses the adopted model unchanged: `c3_research.fit_predict`, i.e. ET 70% + TF-IDF/Ridge 30% with ×1.25 around the training mean.
Seeds are 20260922–24. Each arm predicts every FIN card.

| arm | training sets | features | role |
|---|---|---|---|
| **P** `P_adopted_21` | the 21 research sets | baseline | the current (production) model |
| **F** `F_c3_28` | 21 research sets + EOE, TLA, ECL, TMT, SOS, MSH, HOB | baseline + C3 | **final candidate** |
| P28 `P28_base_28` | 21 + 7 | baseline | decomposition, reported only |
| C21 `C21_c3_21` | 21 | baseline + C3 | decomposition, reported only; time-honest, because all 21 sets precede FIN |

Training tables:
- `data/features/dev_feature_22.csv.gz`, with MH3 dropped, plus `research/gih_llm_extract/c3_features.csv.gz`
- `research/case6/data/new_feature_table.csv.gz` plus `research/case6/c3_features_new.csv.gz`

## FIN inputs
- **Features:** Scryfall via `build_dev_features.fetch_set("FIN")`, unchanged, with `is_supplemental_power_set=0` and `is_premier_set=1` (as for every premier set). This uses Scryfall only.
- **C3:** the unchanged `research/gih_llm_extract/RUBRIC.md` and the same blinded, shuffled procedure (names hidden).
  A text already extracted in case 1 or case 6 is reused. The extraction is committed before any FIN outcome is downloaded.
- **Outcome:** Premier Draft Public Game Data, 28 days from the first draft, cards with ≥ 500 GIH games.
  It uses the same logic as the `all` group of `scripts/case6_aggregate.py`.
- **Matching:** cards are matched by exact name, then by front face. Unmatched cards, such as bonus-sheet reprints, are excluded, as in case 6.

## Order
1. Commit this plan and the locked code.
2. Fetch FIN card texts and features from Scryfall in Actions, with no 17Lands access.
3. Run the blind C3 extraction and commit it.
4. Dry run with synthetic outcomes. This only tests the code path; mechanical fixes are allowed before step 5, and the commit log shows them.
5. **One run** in Actions downloads FIN, aggregates it, scores all arms and commits the results, whatever they are.
   The model is not changed on the basis of FIN afterwards.

## Decision rule
**Rule F.** On FIN, using the 3-seed mean of the metrics:
- F has lower within-set MAE than P, **and**
- F's Spearman is not lower than P's.

If both hold, the final candidate is confirmed. Adopting it at the next production retrain is then the user's decision.
Otherwise it is not confirmed: no adoption is recommended, and the decomposition arms are used only to explain why.

The following are reported but do not enter the decision:
- seed-to-seed ranges
- bias, tail bias and strong/weak recall
- MAE by rarity
- a paired bootstrap of the F − P differences over FIN cards (2,000 resamples, 90% interval)

They are descriptive because this is one set.

## Caveats stated in advance
- FIN was released in June 2025, before the extractor's knowledge ends, so C3 carries the same leakage caveat as the 21-set backtest.
  The post-cutoff evidence for C3 remains MSH and HOB (case 6).
- F is trained on sets released after FIN. They contain no FIN outcomes, but they reflect a later design era. C21 is reported for that reason.
- After this run FIN is no longer a holdout. Whether to add it to production training is a later decision.
- An earlier FIN aggregate artifact was used only for the ALSA final check (run 35692015171). It is not used here.
