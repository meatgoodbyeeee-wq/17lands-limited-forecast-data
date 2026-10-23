# N1 results — neighbour-residual correction: no variant passes (criterion (a) fails for all)

Executed as in PLAN.md (commit 343cd4b). Baseline B10 LOSO OOF (7,075 cards, 28 sets). Outer-fold predictions via nested LOSO (hyper-parameters chosen without the evaluated set, neighbours drawn from other sets only, neighbour residuals from their own OOF predictions). Raw log: `log.txt`.
Reconstruction check (PLAN): text vectors rebuilt from feature tables reproduce the site's top-3 neighbours for 5,344 dev-set cards at 99.9 % (old) / 99.9 % (new), so the 28-set population was used.

| variant | pooled MAE | vs B10 | T_bias (top-10 mean err) | T_mae | Hit@20 | Spearman | sets improved | (a) | (b) | (c) | (d) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B10 | 2.2311 | – | −4.592 | 4.608 | 0.696 | 0.6248 | – | | | | |
| V1 new-method neighbours | 2.2250 | −0.0061 | −4.346 | 4.373 | 0.700 | 0.6275 | 17/28 | fail | ok | ok | ok |
| V2 old-method neighbours | 2.2229 | −0.0081 | −4.382 | 4.406 | 0.711 | 0.6286 | 17/28 | fail | ok | ok | ok |
| V3 tag/type/rarity-weighted | 2.2270 | −0.0040 | −4.366 | 4.391 | 0.707 | 0.6266 | 15/28 | fail | ok | ok | ok |
| V4 tag-group mean residual (ref.) | 2.2312 | +0.0002 | −4.541 | 4.560 | 0.700 | 0.6249 | 15/28 | fail | ok | ok | ok |
| C0 random same-class neighbours (control) | 2.2297 | −0.0014 | −4.560 | 4.575 | 0.700 | 0.6253 | 18/28 | fail | ok | ok | ok |

Pass requires all of (a) MAE gain >= 0.01 pp, (b) |T_bias| not larger, (c) Spearman not lower, (d) >= 15 sets improved. **No variant passes**: the best (V2) gains 0.0081 pp, and per-set paired differences are small (V2 mean −0.0077, s.e. 0.004; V1 −0.0056, s.e. 0.006).
Chosen hyper-parameters sit at the edge of the pre-registered grid (k = 20, alpha 0.2-0.5; V4 alpha 0.5-1.0); by plan the grid was not extended. Non-nested best (descriptive): V1 −0.0102 (k20, alpha 0.3), V2 −0.0082, V3 −0.0056, V4 −0.0016, C0 −0.0022 — only V1 reaches 0.01 and only when tuned on the evaluation sets.

## Top-end (E1)
Neighbour residuals do shift the top-10 error the right way: T_bias −4.59 -> −4.35 (V1) / −4.38 (V2) / −4.37 (V3), T_mae 4.61 -> 4.37-4.41, F_bias (false tops) 0.90 -> 0.61-0.72, Hit@20 0.696 -> 0.700-0.711. Control C0 moves T_bias only to −4.56 and V4 to −4.54. The shift is ~0.25 pp of a ~4.6 pp gap (about 5 %). B_bias (bottom-10) worsens slightly (5.82 -> 5.97-6.00): part of the effect is general regression to the mean of the whole distribution.
AN-tag cards (136): mean error (pred − actual) −0.95 pp in B10 -> −0.68 (V1), −0.80 (V2), −0.58 (V3), −0.73 (V4), −0.92 (C0).

## Named cards (within-set predicted rank; actual rank in brackets)
| card | B10 pred (rank) | V1 | V2 | V3 | V4 |
|---|---|---|---|---|---|
| Avengers Assemble! (MSH, actual 64.5 %, rank 6) | 52.70 (260) | 53.07 (253) | 53.11 (252) | 53.04 (254) | 52.79 (258) |
| Chronicle of Victory (ECL, actual 64.0 %, rank 8) | 53.71 (220) | 54.32 (197) | 54.29 (201) | 54.16 (208) | 53.82 (218) |
Top neighbours of AA (V1): In the Trenches, Laid to Rest, All-Out Assault, Caretaker's Talent, Teleportation Circle (their set-centred residuals +1.5, −6.5, +3.8, +3.9, +6.6 pp) -> weighted correction only about +0.4 pp at alpha 0.3. The neighbours are mostly ordinary cards: nothing in other sets resembles a +2/+2 team anthem bomb, so the borrowed residual is generic.

## By rarity (`by_rarity.csv`)
MAE B10 -> V2: common 1.743 -> 1.737, uncommon 2.242 -> 2.238, rare 2.822 -> 2.806, mythic 3.045 -> 3.032 (V1: 1.740 / 2.239 / 2.815 / 3.011). Largest gains at mythic/rare; commons unchanged (V3 slightly worse for commons). Mean error of the actual top-10 improves for rares (−4.58 -> −4.31 V1) and mythics (−4.32 -> −4.08 V1); uncommons (15 cards) barely.

## Reading and caveats
- The prediction-error of similar cards carries a small but real signal (V1-V3 beat the random control on MAE and clearly on T_bias), yet it is far from the 0.01 pp bar and does not close the top-end gap; consistent with the earlier partial-correlation result (~0.12).
- Gains partly reflect mean-shifting of rare/mythic predictions upward (rare mean error −0.09 -> +0.10 pp), i.e. a calibration effect rather than card-specific insight.
- Residual leakage not removable offline: a neighbour's OOF prediction came from a model trained on all sets except the neighbour's set, i.e. including the evaluated set's outcomes (no residual of the evaluated set is used directly). A fully nested refit (28 x 27 fits) was not run.
- Candidates are the site's reference sets (21 sets with OOF; MH3 has no OOF); the 7 newest sets are targets only. Mana cost for those targets was reconstructed from mana symbols (98.7 % pips agreement on dev sets).
- The metrics, grid and criteria are as pre-registered; nothing was added after seeing results. FRA omitted (no B10 FRA prediction in the repository; data provisional). No TRK data/predictions used. Nothing adopted or deployed.

Files: `summary_by_variant.csv`, `per_set_mae.csv`, `by_rarity.csv`, `named_cards.csv`, `chosen_params.csv`, `result.json`, scripts `label_pool.py` (label vectors), `build_queries.py`, `neighbors.mjs` (site vector(), run against a local checkout of limited-forecast-pages), `lists_py.py` (V3/C0 lists), `n1.py` (analysis). Scripts use absolute scratchpad paths of the session.
