# C3 (LLM-extracted card-effect features): results (2026-09-29)

Plan and decision rule: `PLAN.md` (written before any extraction or model run). FIN not used. MH3 not used. No 17Lands API calls. Pages is unchanged.

## Extraction
- 5,390 unique card texts: the 21 research sets (5,344 rows) plus 290 FRA cards, shuffled with seed 20260929.
  5,370 were read by the extractor in 36 blinded batches (`raw/b00.txt`–`raw/b35.txt`). 20 cards with no rules text were filled by script.
- Extractor: Claude in this session (configured model `claude-opus-5-5`). It saw only mana value, colours, type line, P/T and rules text with the card name replaced by `~`.
- All 5,370 lines pass `check_raw.py` (format, value ranges, full coverage).
- Mean values over the research rows: removal 0.30, sweeper 0.02, bodies 0.60, cards 0.14, repeat 0.24, dependency 0.44, drawback 0.08.

## Comparison (3 seeds; mean, with baseline seed-to-seed range in brackets)

| metric | baseline | C3 | change |
|---|---|---|---|
| pooled MAE (pp) | 2.4931 [0.0013] | **2.3926** | −0.101 |
| pooled Spearman | 0.5089 [0.0005] | **0.5541** | +0.045 |
| within-set MAE (pp) | 2.4908 [0.0014] | **2.3909** | −0.100 |
| within-set Spearman | 0.5219 [0.0005] | **0.5667** | +0.045 |
| strong/weak recall mean | 0.415 [0.009] | **0.457** | +0.042 |
| top-10% bias (pp) | −4.59 | **−4.16** | +0.43 |
| bottom-10% bias (pp) | +5.19 | **+4.82** | −0.37 |
| tail bias sum (pp) | 9.782 [0.007] | **8.985** | −0.797 |
| pred SD / actual SD | 0.524 | 0.563 | +0.039 |

The baseline reproduces the earlier 21-set runs exactly (seed 20260922: MAE 2.49330pp, within-set Spearman 0.52196).
For scale: the regex candidate C1 moved MAE by −0.005pp; C3 moves it by −0.10pp.

Per set (seed 20260922): MAE improves in 20/21 sets, Spearman in 18/21. The largest MAE gains are BRO and LTR (−0.19pp). MOM is the only set that gets worse (+0.06pp); DFT and STX barely move.

## Verdict under the pre-registered rule
**C3 is promising. It passes all five rules.**
1. MAE is not worse: it improves by 0.10pp.
2. Within-set Spearman rises: 0.522 → 0.567.
3. Tails improve: recall rises, and tail bias falls.
4. Set stability holds: 20/21 sets on MAE and 18/21 on Spearman; 12 were required.
5. Every gain exceeds seed noise. The MAE gain is 0.10 against a range of 0.0013; the Spearman gain is 0.045 against 0.0005.

## Leakage caveat (unchanged from PLAN.md)
The extractor's training data includes these 21 sets and probably discussion of how their cards played.
Blinding hides names and numbers, but the extractor can recognise a well-known card from its text. The backtest gain may therefore be optimistic.
**The clean test is FRA**, which was released after the extractor's training cutoff.

### Post-hoc diagnostics (`posthoc.json`; not decision-grade)
- **Field ablation** (seed 20260922, MAE / within-set Spearman):
  - baseline: 2.493 / 0.522
  - facts only (removal, sweeper, bodies, cards, repeat, modal, trick, sink, impact): 2.418 / 0.559
  - judgement only (dependency, drawback, dependency type, friction, net): 2.436 / 0.546
  - full C3: 2.392 / 0.567

  The countable, factual fields carry about three quarters of the gain by themselves. That argues against the gain being mostly a memorised verdict of "this card is bad".
- **By rarity**, the 3-seed-average MAE change is: common −0.04pp, uncommon −0.08pp, rare −0.18pp, mythic −0.29pp.
  This fits leakage, since famous cards are rares. It also fits rules complexity, since rares have the longest and most conditional text and the largest baseline errors. The backtest cannot separate the two.
- **By actual strength within set**: the bottom quintile improves by −0.23pp and the top quintile by −0.26pp; the middle quintiles barely move. The gain is where the audit said the information was missing.
- By type: sorceries improve most (−0.20pp). Lands get slightly worse (+0.03pp).

## Frozen FRA predictions (prospective test)
`fra_frozen_predictions.csv` (sha256 in `fra_frozen_predictions.json`, frozen 2026-09-29 09:34 UTC).
Both arms are fit on all 21 research sets and averaged over the 3 seeds. No FRA outcome data exists yet, and none was used.
- The baseline21 arm matches the adopted FRA predictions in Pages closely: r = 0.992, mean absolute difference 0.15pp. The freeze is a faithful copy of production.
- The C3 arm differs from baseline21 with r = 0.91. Its largest cuts go to build-around rares, for example −4.0pp on a card rated dependency 3. All eight of its largest raises go to cards rated as removal.
- Check once FRA 28-day Public Data exists: does C3 beat baseline21 on FRA MAE and within-set Spearman? This is one set, so it is indicative only.

## Not decided here
Adoption into Pages is a separate, explicit decision by the user. Production use would also need the same rubric extraction for every future set before its predictions are published.

## Files
- `RUBRIC.md`, `build_input.py`, `cards.csv.gz`, `raw/`, `check_raw.py`: the blinded extraction queue and its output
- `c3_research.py`: `features`, `compare` and `freeze` commands; `c3_features.csv.gz` holds one row per `SET|name` / `FRA|id`
- `compare.json`, `compare_oof.csv.gz`: pre-registered comparison (3 seeds, per-set tables, decision)
- `c3_posthoc.py`, `posthoc.json`: post-hoc diagnostics
- `fra_frozen_predictions.csv/.json`: frozen prospective predictions
