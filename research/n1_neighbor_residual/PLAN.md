# N1 — neighbour-residual correction (pre-registered, written before any computation)

Offline re-scoring of EXISTING out-of-fold (OOF) predictions with an add-on correction. No new model fits, no AI judgements (only existing labels/features),
no production / Pages change, no human pre-release evaluations or set reviews. Branch `research/n1-neighbor-residual`, never merged. No TRK data or TRK predictions are used or committed.

## Idea
Earlier check (similar-card actuals): r ~ 0.5 with the target's actual, but the partial correlation with the prediction held fixed was 0.12 and the LOSO error gain ~ -0.016 pp.
Here we borrow the neighbours' *prediction errors* instead of their actuals:

    residual_c = actual_c - OOF_pred_c  (pp), centred by the mean residual of the card's own set
    corrected_t = pred_t + alpha * weighted_mean_{i in N(t)} residual_i

## Baseline and data
- Baseline = B10 LOSO OOF `research/c9_power_questions/oof_B10.csv.gz` (found on main; 7,075 cards, 28 sets, 3 seeds; the same file E1/H1/F1/I1/A2/A3 used). E1 metrics re-implemented from `research/e1_top_card_metric/e1.py` (branch research/e1-top-card-metric) with identical definitions.
- Neighbour candidates = cards of the site reference list (`limited-forecast-pages/data/similar-references.json.gz`, 22 sets) that are in the B10 OOF (21 sets; MH3 has no OOF so it is not a candidate) and have gih_n >= 3000. Candidates always come from sets OTHER than the target's set.
- Neighbour residuals use the neighbour's OOF prediction (model trained without the neighbour's set), never an in-sample prediction.
- Targets = all 7,075 cards of the 28 sets (primary population). Label vectors for all 28 sets are rebuilt exactly as `research/similar_cards/export_labels.py` (checked: identical to the site's similar-labels.json for all 5,344 site cards). Text vectors (site `vector()` from lib/predict.mjs, model.json gih) for the 7 sets absent from the site reference list (ECL, EOE, HOB, MSH, SOS, TLA, TMT) are reconstructed from `research/case6/data/new_feature_table.csv.gz` (colours from color_*, mana cost approximated from mana symbols/mv). Validity check, run before scoring: re-create the same objects for the 21 dev sets and compare top-3 neighbour lists with the site's; if agreement of the old-method top-3 set is < 85 %, variants 1/2 are reported on the 21 dev sets only and the gate (below) is evaluated on those 21 sets for all variants (stated in RESULTS).

## Variants (four, plus one control; each has its own hyper-parameters)
1. **V1 new-method neighbours**: `similarCardsLabelled` score = cos(text) + 0.5 cos(labels), hard filter same class (land/creature/other) and |mv diff| <= 2 (if fewer than k pass, the best non-passing fill up). Weight of a neighbour = score/1.5.
2. **V2 old-method neighbours**: `similarCards`, cos(text) only, no filter. Weight = cos.
3. **V3 tag/type/rarity-weighted neighbours** (fixed definition, not tuned): score = cos(C5 tag block only, i.e. dims c5_* two-letter tags, re-normalised) + 0.5 cos(full label vector) + 0.25 * [same rarity]; same class filter and |mv diff| <= 2 as V1; weight = max(score, 0.01).
4. **V4 reference, tag-group mean residual**: for each C5 tag g (card has tag if c5_g > 0; 80 tags in c5_features), shrunk mean residual m_g = sum(r) / (n_g + 20) over training cards (other sets only), tags with n_g >= 30. Card correction = mean of m_g over its tags (0 if none). No neighbours involved.
5. **C0 control** (descriptive): V1's procedure with k random candidates that pass the V1 filter (fixed seed 20261023). Tests whether any gain is just shrinkage.

Weights: for V1-V3 weighted mean with the weights above.

## Hyper-parameters and nested LOSO
Grid: k in {3, 5, 10, 20} (V1-V3, C0), alpha in {0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0} (all variants). alpha = 0 (no correction) is allowed.
For each outer evaluation set s (28 outer folds): choose (k, alpha) by minimising pooled MAE over the INNER sets t != s, where for an inner target in t the neighbours (V4: training cards) are drawn from sets other than t AND other than s, so nothing of set s (actual or residual) enters the choice. Then apply the chosen (k, alpha) to s with neighbours/training cards from all sets other than s. Ties -> smaller alpha, then smaller k. All metrics below are computed on these outer-fold corrected predictions.
Known unavoidable caveat (stated in RESULTS): the OOF prediction of a neighbour from set u was made by a model trained on all sets except u, which includes s; this leaks no residual of s into the correction directly, but it is not a fully nested refit (that would need 28 x 27 model fits).

## Metrics (all on the 28-set outer-fold predictions; same definitions as e1.py)
Pooled MAE (pp, over 7,075 cards); mean within-set Spearman; E1: T_bias = mean(pred - actual) over each set's actual top-10 (pooled over 28 sets), T_mae, Hit@20, B_bias, F_bias; number of sets whose MAE improves vs B10. Descriptive: effect by rarity (MAE and mean error of the actual top-10 by rarity); AN-tag cards' mean error; within-set rank of Avengers Assemble! (MSH) and Chronicle of Victory (ECL) before/after; non-nested best (k, alpha) per variant. FRA: B10 has no FRA prediction in the repository, so FRA is omitted (28-day data is also provisional until 10/27-28).

## Adoption criteria (ALL must hold, per variant, vs B10)
 (a) pooled MAE lower than B10 by >= 0.01 pp;
 (b) |T_bias| (E1 top-10 mean error) not larger than B10's;
 (c) mean within-set Spearman not lower than B10's;
 (d) MAE improves in more than half of the sets (>= 15 of 28).
Passing = "worth a pre-registered follow-up" only; nothing is adopted or deployed by this study. Failing is reported as is; no variants/grids are added after seeing results.
Disclosure: the idea was motivated after seeing the earlier similar-card analysis and E1 (AA rank 260, ~-4.6 pp top-10 bias); neither is used to tune anything here.
