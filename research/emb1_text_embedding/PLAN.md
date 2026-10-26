# EMB1: text-embedding learner (pre-registered 2026-10-26)

Question: does a dense semantic embedding of card text, learned against actual GIH, add
information to B10 that the TF-IDF/Ridge text part and the AI judgments miss?

Data: 28-set OOF of B10 (`research/c9_power_questions/oof_B10.csv.gz`), card text from
`cards.csv.gz`. Embeddings: bge-base-en-v1.5 and all-mpnet-base-v2 (computed on Actions).
FRA/TRK actuals are not used.

Model E: Ridge on [embedding, rarity one-hot] → set-centred actual GIH, LOSO over 28 sets
(alpha chosen by inner LOSO on the 27 training sets). Prediction = test set's B10 mean + E.

Primary arm (screen): p = (1-w)·B10 + w·E', where E' = E re-centred on the set's B10 mean;
w chosen per test set on the other 27 sets' OOF from grid {0,0.1,...,0.5}. (B10's OOF for
training sets came from models that saw the test set; this affects only one scalar, noted.)

Pass (all required): pooled MAE improves by >= 0.03pp vs B10; within-set Spearman not lower;
MAE improves in >= 17/28 sets; 2025-26 sets (TDM, EOE, SOS, ECL, TLA, MSH, TMT, HOB, DFT, FDN)
not worse in aggregate. Also report each model alone and top-10% under-prediction.
If the screen passes, integrate E as a feature into B10 properly (nested) before adoption.
