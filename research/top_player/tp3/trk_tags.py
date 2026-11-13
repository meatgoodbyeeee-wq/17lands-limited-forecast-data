"""TRK card table (type, text, mana value, colours, rarity, C4 and C5 tags, published B11g) for freeze.py.
Run with the research/trk-shadow tree: python3 trk_tags.py <trk-shadow worktree> <out.csv>. Reads no 17Lands outcome."""
import sys
from pathlib import Path
import pandas as pd
root = Path(sys.argv[1]) / "research"
for p in ("gih_llm_extract", "c9_power_questions", "trk_preview"): sys.path.insert(0, str(root / p))
import trk_label as t  # noqa: E402
q = pd.read_csv(t.LAB / "cards.csv.gz", keep_default_na=False)
fz = pd.read_csv(root / "trk_shadow" / "trk_frozen.csv")
by = {}
for r in q.itertuples(): by.setdefault(t.norm_name(r.name), r)
rows = [by[t.norm_name(n)] for n in fz.name]
raws = {}
for p, (d, bad) in t.load_all().items():
    assert not bad, (p, bad[:3]); raws[p] = d
missing = [r.name for r in rows if not r.auto and any(r.id not in raws[p] for p in ("c4", "c5"))]
assert not missing, missing[:5]
_, t4, t5, _ = t.label_tables(rows, raws, with_c9=False)
out = pd.DataFrame({"set": "TRK", "card_name": fz.name, "type": [r.type_line for r in rows], "text": [r.text for r in rows], "mv": [r.mv for r in rows],
                    "colors": [r.colors for r in rows], "rar": fz.rarity.map({"common": 0, "uncommon": 1, "rare": 2, "mythic": 3}), "auto": [r.auto for r in rows], "pred_overall_pp": fz.G})
out = pd.concat([out, t5.reset_index(drop=True), t4.reset_index(drop=True)], axis=1)
out.to_csv(sys.argv[2], index=False)
print(len(out), "cards; auto", int(out.auto.sum()), "; rarity", out.rar.value_counts(dropna=False).sort_index().to_dict(), "; G mean %.2f" % out.pred_overall_pp.mean())
