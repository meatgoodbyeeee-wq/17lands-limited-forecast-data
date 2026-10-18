# H1 results — Rule F19: Opus borderline-not-reproducible, Haiku not acceptable, averaging does not help

90 decks (30 cards × 3). run1 = A2 Opus, run2 = Opus again, haiku = Haiku.

| pair | EV Spearman | OFF / ON / P Spearman | EV MAD | EV bias | card-level EV MAD |
|---|---|---|---|---|---|
| run1 vs run2 | 0.75 | 0.86 / 0.68 / 0.82 | 0.63 | −0.08 | 0.54 |
| run1 vs Haiku | 0.62 | 0.76 / 0.66 / 0.48 | 1.00 | −0.45 | 0.94 |
| run2 vs Haiku | 0.59 | 0.78 / 0.53 / 0.57 | 1.05 | −0.37 | 1.00 |

Card-level correlation of EV with actual GIH (set-centred, n = 30): run1 Pearson 0.56, run2 0.56, Haiku 0.34, mean(run1, run2) 0.59, mean of three 0.54.
ON gap Rite − Avengers Assemble!: run1 +0.67, run2 +0.67, Haiku +1.00 (same sign in every run).

Rule F19: opus_reproducible = False (EV Spearman 0.75 passes, card-level MAD 0.54 > 0.5 fails); haiku_acceptable = False; averaging_helps = False (+0.03 needed, got +0.025 over run1).

Reading
- Opus repeats itself only moderately: ON is the noisiest component (Spearman 0.68), so a single ON number carries about ±0.5 of noise; more of the same judge adds little (the correlation with actual barely moves).
- Haiku is a weaker judge (card-level r 0.34 vs 0.56) and 0.4 grade points lower; it is not a substitute for ON/EV.
- The Rite > AA ordering of ON is stable across judges, so it is a systematic judgement, not noise: this supports reference-anchored judging (F) over simply repeating judgements.
Process notes: one Haiku and one Opus agent listed/printed other outputs in out_haiku / out_opus2 against instructions (their own judgements were written before; Opus run2 outputs of other decks only, never run1); later Opus prompts forbade it. A1 cards are in the subset on purpose. No production / Pages change.
