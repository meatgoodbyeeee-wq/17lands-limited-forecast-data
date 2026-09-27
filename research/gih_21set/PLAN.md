# 21-set GIH WR improvement research (Premier Draft, BO1)

Research only. No change to the Pages repo, production GIH/ALSA/Deck Color, or FIN.

- Sets: KHM STX AFR MID VOW NEO SNC DMU BRO ONE MOM LTR WOE LCI MKM OTJ BLB DSK FDN DFT TDM
- Excluded completely: FIN (never downloaded), MH3 (rows dropped before any modelling)
- Actuals: official 17Lands Public Game Data, first 28 days, GIH >= 500 games (run 35692015171, preserved in `data/compact_28d/`)
- Baseline: adopted model, ET 600/leaf 8/max_features 0.6 70% + word TF-IDF/Ridge(10) 30%, fixed 1.25 decompression around the training-fold mean

## Step 1: baseline and residual audit (done, run 36302880273)
Reproduces run 36226176884 exactly (pooled MAE 2.4932981507pp, Spearman 0.50884).
Main finding: residuals are flat across *predicted* deciles but range from -5.3pp (actual bottom decile) to +4.6pp (actual top decile).
The model is calibrated given its own prediction and lacks discriminating information. More decompression would not help.
Largest over-predictions are build-around or gated engines. Largest under-predictions are wraths, multi-body token makers, commands and recurring value.

## Step 2: two candidates only
- C1, ability condition/efficiency: mass removal, multi-body, multi-mode, recurring value, token power versus gated triggers, conditions, drawbacks and symmetric effects.
- C2, ability x environment: per-card support of its dependency (spells, artifacts, tokens, graveyard, counters, lifegain, creature type, ...) among that set's C/U booster cards in the card's colours (Scryfall spoiler pool, not 17Lands).
  This differs from the reverted set-level density features in 0d075bc.

## Pre-registered decision rule (written before seeing results)
A candidate is "promising" only if, averaged over 3 seeds and against the baseline averaged over the same seeds:
1. pooled MAE is not worse by more than 0.005pp;
2. within-set mean Spearman improves;
3. tail discrimination improves: the mean of strong_recall + weak_recall rises, or the tail bias magnitude (|top10_bias| + |bottom10_bias|) falls;
4. per-set MAE or Spearman improves in at least 12 of the 21 sets (seed 20260922);
5. any gain exceeds the baseline's seed-to-seed range for that metric.

C1+C2 is reported, but it counts only if both candidates pass on their own.
A pass means "research candidate". Adoption into production is a separate, explicit decision by the user.
