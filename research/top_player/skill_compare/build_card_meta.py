"""Card attributes for the skill comparison (type, mana value, rarity, colours, overall-GIH quality index).
Sources (all already in the repo): research/c14_context_power/set_cards.csv.gz, data/features/dev_feature_22.csv.gz,
research/case6/data/<SET>_case6_28d.csv (overall GIH, used only as a deck-quality index).
Usage: python3 build_card_meta.py <out.csv.gz>"""
import pandas as pd, glob, json, sys
c = pd.read_csv("research/c14_context_power/set_cards.csv.gz")
c["set"] = c.key.str.split("|").str[0]; c["name"] = c.key.str.split("|", n=1).str[1]
c = c.rename(columns={"type": "type_line", "rar": "rarity"})[["set", "name", "type_line", "mv", "rarity", "colors"]]
d = pd.read_csv("data/features/dev_feature_22.csv.gz", usecols=["set", "name", "type_line", "mv", "rarity_ord", "color_W", "color_U", "color_B", "color_R", "color_G"])
d["colors"] = d.apply(lambda r: "".join(k for k in "WUBRG" if r[f"color_{k}"] == 1), axis=1)
d = d.rename(columns={"rarity_ord": "rarity"})[["set", "name", "type_line", "mv", "rarity", "colors"]]
m = pd.concat([c, d[~d.set.astype(str).add("|").add(d.name).isin(c.set + "|" + c.name)]], ignore_index=True)
# 17Lands uses the front-face name for adventure / split / double-faced cards
m["name"] = m.name.astype(str).str.split(" // ").str[0]
m = m.drop_duplicates(["set", "name"])
q = []
for f in sorted(glob.glob("research/case6/data/*_case6_28d.csv")):
    x = pd.read_csv(f, usecols=["set", "card_name", "all_games", "all_wins"])
    x["gih"] = 100 * x.all_wins / x.all_games; x["q_c"] = x.gih - x.gih.mean()
    q.append(x.rename(columns={"card_name": "name"})[["set", "name", "q_c"]])
q = pd.concat(q)
out = q.merge(m, on=["set", "name"], how="outer")
out = out[out.set.isin(q.set.unique())]
BASIC = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
b = out.name.isin(BASIC)
out.loc[b, "type_line"] = "Basic Land"; out.loc[b, "mv"] = 0
out.to_csv(sys.argv[1], index=False)
cov = out[out.q_c.notna()].groupby("set").type_line.apply(lambda s: s.notna().mean())
print("rows", len(out), "| cards with quality index", out.q_c.notna().sum(), "| type coverage of those, by set: min %.3f mean %.3f" % (cov.min(), cov.mean()))
print(cov.round(3).to_dict())
