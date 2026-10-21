#!/usr/bin/env python3
"""TRK (Star Trek) previewed cards from Scryfall only. Runs in Actions (trk_preview_cards.yml).

No 17Lands data. Saves whatever Scryfall lists for e:trk at run time, so it grows as previews come out.
  data/trk_scryfall_raw.json.gz   raw Scryfall card objects (one per card name), for building target.json later
  data/trk_features.csv.gz        build_dev_features.card_features columns (same as the research tables)
  data/trk_cards_text.csv.gz      text columns for blind labelling
  data/fetch_log.json             fetch time and counts
"""
import gzip, json, sys, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import build_dev_features as b  # noqa: E402
import pandas as pd  # noqa: E402

CODE = "TRK"
TEXT_COLS = ["set", "id", "name", "rarity", "collector_number", "mana_cost", "type_line", "oracle_text", "mv",
             "power", "toughness", "booster"] + [f"color_{c}" for c in "WUBRG"]


def fetch_raw(code):
    url = "https://api.scryfall.com/cards/search?q=" + urllib.parse.quote(f"e:{code.lower()}") + "&unique=cards&order=set"
    out = []
    while url:
        d = b.get_json(url)
        out += [c for c in d["data"] if not c.get("digital") or "arena" in c.get("games", [])]
        url = d.get("next_page") if d.get("has_more") else None
        time.sleep(0.12)
    seen, uniq = set(), []
    for c in out:
        if c["name"] not in seen:
            seen.add(c["name"]); uniq.append(c)
    return uniq


def mana_cost(c):
    return c.get("mana_cost") or " // ".join(f.get("mana_cost", "") for f in c.get("card_faces") or [])


def main():
    raw = fetch_raw(CODE)
    out = HERE / "data"
    out.mkdir(parents=True, exist_ok=True)
    with gzip.open(out / "trk_scryfall_raw.json.gz", "wt", encoding="utf-8") as fh:
        json.dump({"set": CODE, "cards": raw}, fh, ensure_ascii=False)
    f = pd.DataFrame([b.card_features(c) for c in raw])
    f.insert(0, "set", CODE)
    f.insert(1, "id", [c["id"] for c in raw])
    f["rarity"] = [c.get("rarity") for c in raw]
    f["mana_cost"] = [mana_cost(c) for c in raw]
    f["booster"] = [int(bool(c.get("booster"))) for c in raw]
    f["is_supplemental_power_set"] = 0
    f["is_premier_set"] = 1
    f.to_csv(out / "trk_features.csv.gz", index=False, compression="gzip")
    f[TEXT_COLS].to_csv(out / "trk_cards_text.csv.gz", index=False, compression="gzip")
    log = {"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cards": len(f),
           "in_booster": int(f["booster"].sum()), "by_rarity": f["rarity"].value_counts().to_dict()}
    json.dump(log, open(out / "fetch_log.json", "w"), indent=1)
    print(log)


if __name__ == "__main__":
    main()
