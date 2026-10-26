# MS1: many-shot judgement with actual-outcome examples (pre-registered 2026-10-26)

Idea: show Opus ~800 past rare/mythic cards (name hidden as ~) with their actual 17Lands GIH
WR minus set mean (pp), then ask it to predict the same quantity for a new set's R/M.

Pilot (done before this plan, used to pick the blend): MSH R/M 82 cards, 3 passes
(pilot_MSH/). Spearman 0.685 vs B10 0.595; MAE blend 0.5·B10 + 0.5·MS 2.575 vs B10 2.758.

Test sets chosen by the user: FRA, HOB (MSH reported as pilot, not counted).
- HOB: examples = 30 R/M per OOF set excluding HOB (27 sets); B10 = 28-set LOSO OOF.
- FRA: examples = 30 R/M from each of the 28 OOF sets; B10 = frozen FRA prediction;
  actual = 17Lands public data (updated 2026-10-17), cards with >= 500 GIH games.
- 3 independent Opus passes per set, same prompt as the pilot; MS = mean of passes.
- Fixed blend p = 0.5·B10Δ + 0.5·MSΔ (Δ = minus set mean of the scored cards). No refit.

Pass (both FRA and HOB): R/M Spearman(MS) > Spearman(B10) AND MAE(blend) < MAE(B10).
Reported also: bootstrap CIs, top-10 under-prediction, per-pass agreement, B10S comparison.
Caveat: FRA contains many famous reprints; Opus may recognise them despite hidden names.
Next step if pass: user decides on a TRK run (R/M) and a wider/all-rarity validation.
