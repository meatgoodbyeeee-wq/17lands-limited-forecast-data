"""N2 shared prep: card table, blinded-text TF-IDF cosine, type category. No residuals used here."""
import re
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
C9 = Path(__file__).resolve().parents[1] / 'c9_power_questions'

def category(tl):
    h = tl.split(' — ')[0]; sub = tl.split(' — ')[1] if ' — ' in tl else ''
    if 'Land' in h: return 'Land'
    if 'Creature' in h: return 'Creature'
    if 'Planeswalker' in h: return 'Planeswalker'
    if 'Instant' in h: return 'Instant'
    if 'Sorcery' in h: return 'Sorcery'
    if 'Artifact' in h:
        return 'Equipment' if 'Equipment' in sub else ('Vehicle' if 'Vehicle' in sub else 'Artifact')
    if 'Enchantment' in h: return 'Aura' if 'Aura' in sub else 'Enchantment'
    return 'Other'

def norm(t):
    t = re.sub(r'\([^)]*\)', ' ', str(t))          # drop reminder text
    return re.sub(r'\s+', ' ', t.lower()).strip()

TOK = r"\{[^}]+\}|[a-z0-9+/\-']+"
def load():
    c = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    c['ntext'] = c.btext.map(norm); c['cat'] = c.type_line.map(category)
    c['ntok'] = c.ntext.map(lambda s: len(re.findall(TOK, s)))
    v = TfidfVectorizer(token_pattern=TOK, ngram_range=(1, 2), sublinear_tf=True)
    X = v.fit_transform(c.ntext)
    return c, X, v
