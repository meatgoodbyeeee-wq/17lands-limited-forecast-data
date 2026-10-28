# G3 retrain (B11g): replace C9 by G3 in B10 — pre-registered before any result (2026-10-28)
Data: G3 single pass per set for all 28 training sets (research/g3_expert_grade/all/<SET>/pass1.json; ECL/TMT = pilot pass1). Keys: keys_all/<SET>.csv.
Arms (28-set LOSO, same ExtraTrees+TF-IDF/Ridge blend 70:30, same seeds/splitting as B10 = c9.run_arm):
- B11g (PRIMARY, "C9 replaced by G3"): B5 numerics + [g3, g3_z (within-set z-score)].
- B11h (diagnostic): B10 numerics (C9 kept) + [g3, g3_z].
Reference: B10 OOF (research/c9_power_questions/oof_B10.csv.gz), B5 OOF.
Evaluation set: the 17 sets NOT used for the lessons (AFR BRO DMU ECL HOB KHM LTR MID MOM MSH NEO ONE SNC STX TMT VOW WOE). The 11 lesson sets (BLB DFT DSK EOE FDN LCI MKM OTJ SOS TDM TLA) are reported but not used for the decision (G3 saw their largest AI-vs-expert gaps).
Metrics: pooled MAE (pp, per-set) and per-set sign count, mean within-set Spearman, MAE of the top-decile cards (by actual GIH).
Decision rule: use B11g for TRK if on the 17 sets  MAE(B11g) <= MAE(B10) + 0.02pp  AND mean Spearman(B11g) >= Spearman(B10) - 0.005.
 (User has already decided to adopt G3; the rule only decides whether the retrained model is safe to use. If it fails: report, and fall back to B10-with-G3-added (B11h) if B11h < B10 by >= 0.02pp, else ask the user.)
Note: training G3 is a single pass; TRK G3 = mean of 3 passes (lower noise) — documented mismatch.
