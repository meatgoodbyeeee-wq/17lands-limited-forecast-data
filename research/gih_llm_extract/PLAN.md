# C3: LLM-extracted card-effect features for GIH WR (proposal 1)

Research only. No change to the Pages repo or production predictions. FIN and MH3 are not used.

## Why
The 21-set residual audit (`research/gih_21set/RESULTS.md`) found the error is missing information, not calibration:
build-around / gated engines are over-predicted; wraths, multi-body token makers, modal spells and recurring value are under-predicted.
C1 targeted the same axes with regular expressions and moved MAE by only −0.005pp. Hypothesis: regex detection quality is the bottleneck,
and reading the rules text (removal quality, bodies, card advantage, conditions, drawbacks) fixes it.

## Extraction
- Extractor: Claude (this Claude Code session, configured model `claude-opus-5-5`), in-context, following `RUBRIC.md` exactly.
- Cards: the 21 research sets (5,344 rows; identical text+type+cost annotated once) plus the 290 FRA cards, mixed and shuffled with a fixed seed.
- Blinding: the extractor sees only mana cost, type line, power/toughness and rules text. Card name (replaced by `~` in text), set, rarity and all 17Lands numbers are hidden.
  FRA gallery text is normalized to Scryfall style first (apostrophes, CRLF, `{oX}` symbols).
- Basic lands and cards with no rules text are filled with zeros by script, not by the extractor.
- The rubric asks for facts about the text (what it removes, how many bodies, what it depends on), never for "how strong is this card".

## Leakage caveat (stated before results)
The extractor was trained on data that includes these historical cards and, likely, discussion of how they performed.
Blinding and a factual rubric reduce but cannot remove this. A 21-set backtest gain may therefore be optimistic.
FRA was released after the extractor's training cutoff, so FRA is a clean prospective test:
**regardless of the backtest verdict, freeze FRA predictions from the 21-set baseline and from baseline+C3 now**, and compare them once FRA's 28-day Public Data exists.

## Candidate (one only)
C3 = baseline features + 26 columns built mechanically from the rubric fields:
- 10 raw fields: `llm_removal, llm_sweeper, llm_bodies, llm_cards, llm_repeat, llm_modal, llm_dependency, llm_drawback, llm_trick, llm_sink`
- 12 one-hot dependency categories: `llm_dep_T, _G, _A, _E, _S, _K, _C, _L, _X, _H, _M, _O`
- 4 composites (fixed, not tuned): `llm_impact = removal + 2·sweeper + max(bodies−1, 0) + cards + repeat + modal`,
  `llm_friction = dependency + drawback`, `llm_net = impact − friction`, `llm_impact_per_mv = impact / max(mv, 1)`

Model, folds and seeds are identical to `scripts/gih21_research.py` (ET 70% + TF-IDF/Ridge 30%, ×1.25; seeds 20260922–24).
The baseline is re-run in the same environment so both arms share library versions.

## Pre-registered decision rule (same as research/gih_21set/PLAN.md)
C3 is "promising" only if, averaged over 3 seeds and against the baseline averaged over the same seeds:
1. pooled MAE is not worse by more than 0.005pp;
2. within-set mean Spearman improves;
3. tail discrimination improves: mean of strong_recall + weak_recall rises, or |top10_bias| + |bottom10_bias| falls;
4. per-set MAE or Spearman improves in at least 12 of the 21 sets (seed 20260922);
5. any gain exceeds the baseline's seed-to-seed range for that metric.

Prospective FRA check (indicative only, one set): C3 should beat the baseline on FRA MAE and within-set Spearman.
Adoption into production is a separate, explicit decision by the user.
