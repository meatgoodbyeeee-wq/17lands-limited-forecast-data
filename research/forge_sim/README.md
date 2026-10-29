# Forge self-play: colour-pair strength (FRA first)

User request 2026-10-29: raise the play strength of Forge's AI and estimate colour-pair strength by self-play of fixed-rule decks
(about 10 per pair, mostly commons and uncommons), best of one like Premier Draft. Started on FRA. Research only; Pages unchanged.

- `build_decks.py` — 10 decks per pair (pools of 45 weighted by booster frequency, 23 best spells by the frozen B10 prediction, 17 basics) → `decks_fra/`
- `run_sim.py` — Forge `sim -t RoundRobin -m 1` on random subsets (2 decks per pair per round) → `runs/<name>.csv` (one row per game)
- `card_wr.py` — card win rate when drawn (needs `run_sim.py --seen` and `forge_seen.patch` applied to Forge) against 17Lands GIH WR
- `analyze.py` — pair win rates and Spearman with 17Lands Color Ratings (`research/fra_check/fra-actual-color-ratings.json`)

Forge: Card-Forge/forge master (2.0.16-SNAPSHOT, 2026-10-29), built with `mvn -pl forge-gui-desktop -am -DskipTests package`; all 285 FRA cards are scripted.

## Results
| run | AI | games | Spearman vs 17Lands (95% CI) | sim pair SD |
|---|---|---|---|---|
| `runs/fra_default_mcoff` | Default, Flat Monte Carlo off | 2,470 | −0.36 (−0.61..0.08) | 4.8pp (actual 1.6pp) |
| same, vs splash combined (`actual/fra-color-ratings-splash-combined.json`) | | | −0.02 (−0.39..0.39) | 4.8pp (actual 1.2pp) |

| `runs/fra_default_mcoff_seen` (same seeds and pairings, re-run with drawn-card log) | Default, MC off | 2,470 | +0.27 (−0.13..0.69) vs splash combined | 5.1pp (actual 1.2pp) |

Re-running the same seeds moved Spearman from −0.02 to +0.27: Forge games are not reproducible across runs and 467 games per pair
(±2.3pp) are not enough to order pairs whose actual spread is 1.2pp.

## Cards the AI misplays (`runs/fra_default_mcoff_seen_cards.csv`, card_wr.py)
Forge's AI has no logic for FRA's Empower Jace (`ApiType.Empower` is missing from forge-ai `SpellApiToAi`, so it falls back to
`CannotPlayAi`): any spell with Empower, even as a rider, is never cast. 35 FRA cards use Empower; Protege's Awakening,
No Admittance, Academic Ascent, Violent Echoes, Tam's Resistance and Countersculpt stay in hand in 85–92% of the games they are drawn
(all cards: 17%). Decks average 3.2 (BR) to 8.1 (UG) Empower cards; UG, WU and UR are the pairs with most and rank at the bottom
of the baseline. Card win rate when drawn agrees little with 17Lands GIH WR (Spearman +0.11, within-deck IWD +0.07, 108 cards).

Comparison target (user request): two-colour decks with and without a splash, `actual/fra-color-ratings-splash-combined.json`
(17Lands Color Ratings, combine_splash=true, fetched by `.github/workflows/forge_sim_color_ratings.yml`). Splash-combined actual order: WU, UB, RG, UR, BG, WG, BR, WB, WR, UG.

Baseline reading: the order is close to reversed; blue decks (WU, UR: actual 1st and 2nd) come 9th and 10th, consistent with the AI being weak with tempo/control.
