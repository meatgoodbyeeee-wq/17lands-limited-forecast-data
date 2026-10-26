# N2 — near-duplicate residual correction (pre-registered, written before any residual-based computation)

Offline re-scoring of EXISTING B10 out-of-fold (OOF) predictions. No model fits, no AI judgements, no production / Pages / TRK file changes. Branch `research/n2-near-duplicate` (from `research/n1-neighbor-residual`), never merged.
FRA and TRK actuals are not used (FRA actuals exist in the repository but are not read). N1 (all similar cards) was not adopted (gain -0.0081 pp < 0.01); N2 restricts to "nearly the same effect" pairs only.

## Data
- B10 LOSO OOF: `research/c9_power_questions/oof_B10.csv.gz` (7,075 cards, 28 sets). Residual r_i = (actual - pred) x 100 pp, centred by the mean residual of the card's own set (as N1).
- Card text: `research/c9_power_questions/cards.csv.gz` (name-blinded `btext`, `type_line`, `mv`; joined on `set|name`; same pool as `c9.load_pool()`).

## Definition of "near-duplicate" pair (c in target set S, d in another set)
1. Text: `btext` lower-cased, reminder text in parentheses removed. TF-IDF (word 1-2 grams, tokens = words/numbers/`+1/+1`/`{mana}` symbols, sublinear tf, idf fit on all 7,031 unique card texts - unsupervised) cosine similarity >= threshold.
2. Both texts have >= 6 tokens after normalisation (excludes keyword-only/vanilla cards, which would match trivially).
3. Same card category from type_line (Land, Creature [incl. artifact creature], Planeswalker, Instant, Sorcery, Equipment, Vehicle, other Artifact, Aura, other Enchantment).
4. |mv_c - mv_d| <= 1.
5. Different set, and different card name (reprints of the same card are excluded, to test genuinely different cards).
Thresholds were chosen from the pair-count distribution only (no residual was looked at). Counts of cards with >=1 partner (cos threshold: cards / pairs): 0.95: 290 / 280; 0.90: 392 / 470; 0.80: 638 / 1,053 (all with rules 2-5; 0.85: 509 / 694; 0.75: 858 / 2,158). Script `dist.py`.
- **Primary threshold: cosine >= 0.90.** Report-only: **0.95** and **0.80**. Nothing else is tried.

## Correction
For target card c (set S) with matches M(c) (cards of other sets, rule above), n = |M(c)|:
    corrected_pred_c = pred_c + n/(n+k) * mean_{d in M(c)} r_d,   **k = 1** (fixed).
No match -> no correction. Neighbour residuals are the neighbours' own OOF residuals (set-centred). No tuning of anything (no alpha, no k, no threshold search).

## Rule N2 (all must hold, primary threshold)
1. MAE of the corrected cards only is lower than B10's on the same cards.
2. Paired card-level difference d_i = |err_new| - |err_B10| over corrected cards: bootstrap over cards (10,000 resamples, seed 20261026), 95 % percentile interval; upper bound < 0.
3. Pooled MAE over all 7,075 cards (28 sets) not worse than B10.
4. Mean within-set Spearman (28 sets) not lower than B10's by 0.0005 or more.
Passing = "worth a follow-up" only; nothing is adopted/deployed here. Failing is reported as is.

## Reporting
Number of corrected cards and pairs per threshold; Rule N2 numbers at all three thresholds (judgement on the primary only); top pairs by effect; breakdown by rarity and by category; pairs with identical name excluded (their count reported). Reference only (not in judgement): Tricorder (TRK) - number of matches among the 28 sets with the same definition and the correction amount (pp); no TRK prediction or actual is written.

## Known limitations
- OOF residuals of the neighbour come from a model trained on all sets except the neighbour's set, i.e. including the evaluated set S's outcomes (same caveat as G2/N1). Not a fully nested refit.
- Matching is text-only plus type/mv; P/T, colour and rarity are not compared.
- Residuals of matched partners are mutually used (c uses d's residual and d uses c's); the bootstrap resamples cards, not pairs, so intervals may be somewhat optimistic.
