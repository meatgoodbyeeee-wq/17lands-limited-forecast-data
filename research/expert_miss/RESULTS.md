# Why do experts miss? (2026-10-29, exploratory) — em.py
13 sets with pre-release expert grades (3,251 cards). Expert-implied forecast = LOSO linear map of within-set grade z to within-set GIH (pp).
- Expert-implied MAE 2.111 vs B10 2.122 (same level). corr(expert residual, B10 residual) = 0.755 -> they mostly miss the SAME cards.
- Expert squared error explained by colour within set: 9.4% (null from permutation 2.4% -> real excess 7%); + rarity: excess 7.5%.
  Per-set colour misjudgement SD 0.91pp (largest: OTJ green +2.5, OTJ blue -2.0, TDM black -2.0, BLB red -1.7).
- By grade: experts compress the top (grade >= 3.5: +0.84pp under), B10 more so (+1.87).
- By type: non-creature, non-spell permanents (enchantments, auras, equipment, artifacts) are overrated by experts (-0.46pp; B10 +0.03).
  Cheap creatures (MV 1) underrated by experts +1.33 (B10 +0.97).
- Largest misses (qualitative):
  UNDER: converge / fixing cards in a 5-colour set (SOS Arcane Omens, Together as One, Archaic's Agony; TMT Everything Pizza)
         -> value depends on how much fixing the whole set has; multi-level Class enchantments (TMT); conditional copy cards whose
         condition was easy in the set; finishers/"exactly 10 life" style cards (GIH WR inflated because they are cast when winning).
  OVER:  value-engine enchantments/equipment/auras graded 3-3.5 that do nothing to the board (MKM Connecting the Dots, Case of the
         Gorgon's Kiss, Assemble the Players; TLA Avatar Destiny; OTJ Key to the Vault; ECL Collective Inferno); spells-matter legends
         needing deck support (Judith, Alania, Fire Lord Zuko); "do-nothing" build-arounds.
Reading: experts and B10 share ~57% (0.755^2) of their residual variance. Expert-specific blind spots that look systematic:
(1) set-level context (colour strength, fixing density for converge/multicolour), (2) overrating non-board value engines,
(3) top compression, (4) GIH WR measurement effects (cards cast when already winning). The rest is card-specific.
