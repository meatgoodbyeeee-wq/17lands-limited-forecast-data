# TRK preview Step 1: Sonnet as B10 labeller on 100 FRA cards (Rule S1) — not supported

Pre-registered in PLAN.md (commit 3473cce) before any labelling. No outcomes used. Production, Pages and TRK_PLAN.md unchanged.

- Reproduction: B10 with all-Opus labels reproduces the frozen FRA `pred_B10` (max diff 2.2e-16).
- Labels: 6 Sonnet passes, 100 cards each, all valid. One C3 line (card #2, modal = 2, out of range) was sent back to the same labeller and corrected before scoring.

## Rule S1 (B10 with Sonnet labels S vs Opus labels O, 100 cards)
| arm | mean abs pp | mean pp | Pearson | max abs pp |
|---|---|---|---|---|
| **S (all four swapped)** | **0.679** (≤ 0.40 ✗) | −0.080 (≤ 0.20 ✓) | **0.942** (≥ 0.95 ✗) | 6.97 |
| only C3 | 0.130 | +0.071 | 0.997 | 1.17 |
| only C4 | 0.059 | +0.015 | 0.999 | 0.54 |
| only C5 | 0.116 | −0.032 | 0.998 | 0.61 |
| only C9 | 0.632 | −0.126 | 0.950 | 6.54 |
| C3 + C4 + C5 (not pre-registered, added after S1 failed) | 0.232 | +0.053 | 0.994 | 1.18 |

**Rule S1 not supported.** The gap is almost all C9: swapping only C9 moves predictions about as much as the whole B10-vs-B5 difference (0.61 pp).
By rarity (S): mythic mean −0.47 pp, mean abs 1.16; rare −0.12 / 0.72; uncommon +0.07 / 0.51; common +0.09 / 0.46. Sonnet lowers mythics.

## Labels (Sonnet vs Opus, means over the 3 C9 passes)
C9 Spearman: IMP 0.93, UNA 0.79, VAL 0.79, FLOOR 0.86, FLEX 0.87, PLAY 0.91, GRADE 0.91. Mean GRADE 4.48 vs 4.64; FLOOR 2.04 vs 1.81; IMP 1.83 vs 1.66; FLEX 1.13 vs 1.31.
Largest shifts: Necrodominance −6.97 pp, Ajani's Anguish −3.50, Omnipresence −3.03, Hexhaven Invigorator +2.63, Puppet Crafting −2.59.
Top 10 by O keep 9 of 10 places within the top 11 under S.

## Implication
The user decides the TRK labeller. Options: Opus for all passes (matches training); or Sonnet for C3/C4/C5 and Opus for C9 (0.23 pp mean abs from O in this sample, reported arm only).

# Step 2: TRK previewed cards, batch 1 (2026-10-22) — preliminary B10 predictions

User decision 2026-10-22: run the recommended split on the previewed cards. Labellers: C3, C4, C5 by Sonnet; C9 passes p1–p3 by Opus. All blind (name → "~"), same rubrics and card view as production, ids fixed in `label/ids.csv`.
- Cards: Scryfall `e:trk` at 2026-10-22 05:00 UTC, 165 cards; 5 basic lands set to zero labels, 160 labelled; all 960 label lines valid on the first read (`trk_label.py check`).
- Prediction: B10 with the production 28-set training pool and seeds (FRA not used), `pred_b10.csv`, 160 non-basic cards. Mean 55.79, SD 2.13, range 49.68–63.75 (pre-registered sanity range for the set SD is 1.5–3.0; FRA 2.22).
- Caveats: previews over-represent rares and mythics, so the mean is not a set mean; Spacecraft, Sagas and other new TRK mechanics lie outside what the model was trained on; the labels mix Sonnet (C3–C5) and Opus (C9), which Step 1 showed shifts B10 by about 0.23 pp on average relative to all-Opus. These are preliminary; the full-set run after 10/31 replaces them. Not published; Pages and production unchanged.

# Step 3: TRK full set, B11g + one-line reasons (2026-10-31)
- Cards: official gallery 296 (2026-10-30 21:39 UTC, not marked complete) + 15 cards that Scryfall lists but the gallery does not yet
  (added to the Pages card list as manual entries, no image) = 311. Scryfall's 17 missing collector numbers are exactly the 17 gallery-only main-set cards.
- Labels: batch 5, C3/C4/C5 by Sonnet for 71 new cards (311 labelled, all valid). C9 not used.
- G3 full run: 3 Opus passes on all 311 cards (whole-set context); pass agreement Pearson 0.926 / 0.928 / 0.905.
- B11g export (no spread factor, user decision 2026-10-29): 311 cards, set mean 55.40, median 55.23, range 48.12-63.76, SD 2.34; identical to e.predict;
  SHAP reconstruction error 1e-9. Range M5 (28-set coverage 0.80).
- Reasons: 8 Opus batches, 311 sentences "〜ため、〜。"; 5 sentences lacked the comma after ため (fixed by hand), then check ok.
- Pages: private preview artifact updated (version 12). Not published (TRK available:false). Predictions, G3 passes and reasons stay local (gitignored).
