"""Compute sentence embeddings of card text (runs on GitHub Actions; HF is unreachable from the sandbox)."""
import sys, numpy as np, pandas as pd
from sentence_transformers import SentenceTransformer
u = pd.read_csv('research/c9_power_questions/cards.csv.gz', keep_default_na=False)
def txt(r):
    pt = f' {r.pt}.' if r.pt else ''
    return f"{r.type_line}. Mana value {r.mv}. Colors {r.colors or 'colorless'}.{pt} {r.btext}"
T = [txt(r) for r in u.itertuples()]
for name, tag, prefix in [('BAAI/bge-base-en-v1.5', 'bge', ''), ('sentence-transformers/all-mpnet-base-v2', 'mpnet', '')]:
    m = SentenceTransformer(name, device='cpu')
    E = m.encode([prefix + t for t in T], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    np.savez_compressed(f'research/emb1_text_embedding/emb_{tag}.npz', id=u['id'].values, E=E.astype(np.float16))
    print(tag, E.shape)
