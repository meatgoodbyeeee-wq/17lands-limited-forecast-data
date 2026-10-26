# EMB1 results (2026-10-26): FAIL

| | pooled MAE | within-set Spearman |
|---|---|---|
| B10 | 2.231 | 0.625 |
| E alone, bge-base | 2.683 | 0.403 |
| E alone, mpnet | 2.700 | 0.406 |
| blend (w by inner LOSO) | 2.231 | 0.625 |

The inner-LOSO weight was 0 for every one of the 28 test sets with both embeddings, so the
blend equals B10 exactly (0/28 sets improved). Generic sentence embeddings of rules text carry
less GIH signal than the existing TF-IDF + judgement features and add nothing on top of them.
Not pursued further. Files: result.json, oof_emb1_{bge,mpnet}.csv.gz.
