# Forge self-play: colour-pair strength (FRA first)

User request 2026-10-29: raise the play strength of Forge's AI and estimate colour-pair strength by self-play of fixed-rule decks
(about 10 per pair, mostly commons and uncommons), best of one like Premier Draft. Started on FRA. Research only; Pages unchanged.

- `build_decks.py` — 10 decks per pair (pools of 45 weighted by booster frequency, 23 best spells by the frozen B10 prediction, 17 basics) → `decks_fra/`
- `build_pool_decks.py` — alternative (user request): one whole-colour-pool deck per pair, every common ×2 and uncommon ×1 + lands at 17:23 → `decks_fra_pool_c2u1/` (≈162 cards)
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

## Before and after the AI fixes (two runs each, seeds 1 and 2, 4,940 games per setting; FRA splash combined)
| setting | runs | pair Spearman vs 17Lands (95% CI) | sim pair SD (actual 1.2pp) | run-to-run Spearman | card GIH vs 17Lands GIH (IWD) | held |
|---|---|---|---|---|---|---|
| unfixed | `fra_default_mcoff_seen`, `fra_default_mcoff_s2` | +0.02 (−0.20..0.39) | 5.1pp | 0.70 | +0.16 (+0.23), 146 cards | 16.9% |
| fixed | `fra_fixed_mcoff_s1`, `fra_fixed_mcoff_s2` | +0.02 (−0.33..0.38) | 3.4pp | 0.66 | +0.32 (+0.29), 152 cards | 11.8% |

Card tables: `runs/fra_default_pool_cards.csv`, `runs/fra_fixed_pool_cards.csv`. The fixes bring card results closer to 17Lands and
shrink the pair spread, but the pair order still does not match (fixed: WR 1st vs actual 9th, RG 9th vs 3rd, UR 10th vs 4th).
Runs agree with each other (run-to-run Spearman 0.66–0.81), so the mismatch is systematic (AI play or the fixed-rule decks), not noise.

## Whole-colour-pool decks (`runs/fra_pool_c2u1`, fixed AI incl. fix 4, 55 rounds × 45 games = 2,475)
One deck per pair (commons ×2, uncommons ×1, ≈162 cards). Spearman vs 17Lands splash combined +0.12 (95% CI −0.48..0.33),
sim pair SD 3.0pp, split-half (odd vs even rounds) 0.38, mean game 9.7 s. Blue pairs are still at the bottom (UB 10th vs actual 2nd,
UG 9th, UR 7th); RG, WG, WB on top. For reference, the copy-weighted mean 17Lands GIH WR of each pool deck, with no games at all,
has Spearman +0.35 with the actual pair order, and −0.24 with the sim order: the AI, not the card choice, now drives the mismatch.

## Why the blue pairs lose (pool decks; 180 games with full logs, `log_metrics.py`)
- UB and UG win 14–18% of games of 12 turns or fewer and 37–48% of 13–20 turns, but 49–55% of longer games.
- Mana use per turn (lands tapped / lands) and casts per turn are about the same for every pair: blue decks do not leave more mana idle.
- Instants are played like sorceries: only 13% of instant / flash casts happen on the opponent's turn; removal and bounce are cast
  mostly in the AI's own upkeep or draw step (Wrath of the Bloodmane 23 of 39, Unsummon 26 of 39), almost never against attackers.
  Countersculpt was cast 6 times in 180 games. Every deck blocks only about 20% of the attackers it faces.
- Across the 10 pool decks, the share of instants has Spearman −0.60 with the sim win rate (UR 20%, UG 18%, UB 18% instants are
  7th, 9th and 10th); creature count +0.39. The AI's sorcery-speed use of instants is the main weakness left.

## Why UR is last (fixed runs, `fra_fixed_mcoff_s1/s2`)
- Short games: UR wins 32% of games of 12 turns or fewer (both players' turns; WR and WB win 77% of them) vs 42–49% of longer games.
- Decks: the fixed-rule builder gives UR the fewest creatures of mana value ≤ 2 (3.5 per deck; RG 7.0, WB and WG 6.3) and the highest
  average mana value (3.30). One deck, FRA_UR_01, wins 28.5% of 144 games.
- Card types: against 17Lands, the AI gets less out of instants and sorceries than out of creatures (mean percentile gap of
  within-deck win rate vs GIH WR: creatures +0.09, instants/sorceries −0.18, removal among them −0.23). UR's 6.5 spells per deck and
  burn (Wrath of the Bloodmane: cast in 97% of draws, 38% win rate in UR when drawn) suffer from this.
- Prepare (21 FRA cards) works: in a 15-game probe the AI cast the prepared spells (e.g. Unwind History 7 times for 7 Diviners).
- Still held but legitimately: second copies of legendary cards (Way of the … enchantments, Mabel, Kiora, Ruric Thar), board wipes
  (Overwrite the Multiverse, Austere Command), Proft (threshold). The one remaining AI gap was Jace's Machinations (fix 4).

## Cards the AI misplays (`runs/fra_default_mcoff_seen_cards.csv`, card_wr.py)
Forge's AI has no logic for FRA's Empower Jace (`ApiType.Empower` is missing from forge-ai `SpellApiToAi`, so it falls back to
`CannotPlayAi`): any spell with Empower, even as a rider, is never cast. 35 FRA cards use Empower; Protege's Awakening,
No Admittance, Academic Ascent, Violent Echoes, Tam's Resistance and Countersculpt stay in hand in 85–92% of the games they are drawn
(all cards: 17%). Decks average 3.2 (BR) to 8.1 (UG) Empower cards; UG, WU and UR are the pairs with most and rank at the bottom
of the baseline. Card win rate when drawn agrees little with 17Lands GIH WR (Spearman +0.11, within-deck IWD +0.07, 108 cards).

## AI fixes (`forge_ai_fixes.patch`, forge-ai; apply with `forge_seen.patch`)
1. `SpellApiToAi`: Empower → `AlwaysPlayAi` (was unassigned → `CannotPlayAi`).
2. `AiController.checkETBEffects`: a creature whose mandatory ETB the AI would skip if it were optional (no good target, self-mill,
   loot) is still cast when the ETB can resolve (`doTrigger(..., mandatory=true)`); before, Mabel, Bitter Recluse, Primal
   Witchstalker, Yoshimaru, Seasoned Cryomancer and others stayed in hand 31–85% of the games they were drawn.
3. `CountersPutAllAi.chkDrawback`: a beneficial counter sweep as a spell's rider is fine unless it helps the opponent more
   (Command the Stage was refused with no other Wizard tokens: 94% held).
4. Card script `jaces_machinations.txt`: `AILogic$ Always` (its main `Effect` had no AI logic: 91% held even after fix 1;
   probe: cast in 8 of 8 draws). Added after the two fixed runs; the runs above do not include it.
Probe (66 games, 12 decks): share of drawn spells held to the end 17.0% → 8.9%; Empower spells 85–92% → 4–8% (Countersculpt 55%,
a counterspell waiting for a target). Known leftovers: Sublime Epiphany's copy mode has no drawback AI (`CopyPermanentAi`);
Violent Echoes' `Excess` SVar warns before resolution (it is cast).

Comparison target (user request): two-colour decks with and without a splash, `actual/fra-color-ratings-splash-combined.json`
(17Lands Color Ratings, combine_splash=true, fetched by `.github/workflows/forge_sim_color_ratings.yml`). Splash-combined actual order: WU, UB, RG, UR, BG, WG, BR, WB, WR, UG.

Baseline reading: the order is close to reversed; blue decks (WU, UR: actual 1st and 2nd) come 9th and 10th, consistent with the AI being weak with tempo/control.
