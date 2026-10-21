# TRK preview: B10 on previewed cards, labelled by Sonnet — pre-registered 2026-10-21

Research only. Production `gih-c3-28set-20260929`, Pages and `research/newset/TRK_PLAN.md` (branch `trk-support`) are unchanged.
Nothing here reads FRA, TRK, FIN or MH3 outcomes.

## User decision (2026-10-21)
The user asked to start B10 evaluation of TRK from the previewed cards as they come out, with the AI labelling done by Sonnet.
This departs from two defaults in `TRK_PLAN.md` ("model stays production", "no early extraction of previewed cards").
Those defaults still govern what is published; whether B10 is used for the published TRK forecast stays a separate user decision.

## Step 1: is Sonnet a valid labeller for B10? (FRA 100-card check, run before any TRK labelling)
All C3, C4, C5 and C9 labels that B10 was trained on were made by Opus (`claude-opus-5-5`). Sonnet labels may sit on a different scale.

- **Sample**: 100 FRA cards from `limited-forecast-pages/data/target.json.gz`, excluding cards whose label is automatic (basic lands, blank text);
  25 common, 30 uncommon, 25 rare, 20 mythic, drawn with seed 20261021 (`sonnet_check.py sample`). Written to `fra100/sample.csv` before labelling.
- **Labelling**: Sonnet subagents, one per pass, six passes: C3, C4, C5, C9 p1, C9 p2, C9 p3. Each uses the unchanged rubric of that extraction
  (`gih_llm_extract/RUBRIC.md`, `c4_fine_effects/RUBRIC.md`, `c5_atomic_effects/RUBRIC.md`, `c9_power_questions/RUBRIC.md`) and the same blinded
  card view as production (name as `~`; no set, rarity or numbers). Card order: as sampled for C3/C4/C5/C9 p1, reversed for p2, shuffled for p3.
  Labellers are told not to use memory of the card or set; no agent sees another pass.
- **Comparison**: B10 predictions for the 290 FRA cards computed twice with the same code and seeds as `c9_power_questions/freeze_fra.py`:
  (O) all Opus labels; (S) the 100 sampled cards' C3/C4/C5/C9 columns replaced by Sonnet labels. (O) must reproduce the frozen `pred_B10` (max diff < 1e-9).
  Measured on the 100 cards, S − O in pp.
- **Rule S1 (Sonnet accepted as B10 labeller)**: all three hold —
  1. mean |S − O| ≤ 0.40 pp (for scale: B10 vs B5 on FRA differ by 0.61 pp),
  2. |mean (S − O)| ≤ 0.20 pp (no systematic shift),
  3. Pearson(S, O) ≥ 0.95.
- **Reported, not decisive**: the same differences when only one extraction is swapped (C3 only, C4 only, C5 only, C9 only); per-field label
  agreement Sonnet vs Opus (Spearman, exact-match share, mean difference), next to the Opus inter-pass agreement in `c9_power_questions/agreement.json`;
  the rank change of the top 10 cards by O.
- **If S1 fails**: report to the user which extraction causes the gap and let the user choose (Opus labelling for TRK, or another option). No recalibration is applied without a new pre-registration.

## Step 2: TRK previewed cards (only if S1 passes, or the user decides otherwise)
- Card source: Scryfall `e:trk` via Actions (`trk_cards.py`, `.github/workflows/trk_preview_cards.yml`), refreshed as previews come out.
  Basic lands are excluded. Cards that are not in draft boosters are flagged when that information exists.
- Labels: Sonnet, the same six passes and blinding as Step 1, in batches of newly previewed cards. Labels are appended; a card already labelled is not relabelled.
- Prediction: B10 with the production training pool and seeds (FRA not used for training), written to `trk_preview/pred_b10.csv` with the card list date.
  These are preliminary; the full-set run after 10/31 replaces them. No manual correction of predictions, no human pre-release evaluations as input.
