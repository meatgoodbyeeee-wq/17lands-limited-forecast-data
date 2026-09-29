#!/usr/bin/env python3
"""Build the blinded, shuffled extraction queue for C3 (see PLAN.md).

Writes cards.csv.gz: one row per unique (text, type, mv, P/T) with a shuffled integer id, the blinded fields
shown to the extractor, and the (set, name) keys it maps back to. FIN and MH3 are refused.

  python build_input.py --fra <pages>/data/target.json.gz          # build queue
  python build_input.py --show 3                                     # print batch 3 (blinded)
"""
import argparse
import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEAT = ROOT / "data/features/dev_feature_22.csv.gz"
OUT = HERE / "cards.csv.gz"
RESEARCH_SETS = {"KHM", "STX", "AFR", "MID", "VOW", "NEO", "SNC", "DMU", "BRO", "ONE", "MOM",
                 "LTR", "WOE", "LCI", "MKM", "OTJ", "BLB", "DSK", "FDN", "DFT", "TDM"}
SEED = 20260929
BATCH = 150


def gallery_to_scryfall(s: str) -> str:
    s = (s or "").replace("’", "'").replace("\r\n", "\n")
    return re.sub(r"\{o([^}]*)\}", lambda m: "".join("{" + x.strip("()").upper() + "}" for x in m.group(1).split("o") if x), s)


def blind(text: str, name: str, type_line: str) -> str:
    names = [n.strip() for n in name.split("//") if n.strip()]
    for n in sorted(names, key=len, reverse=True):
        text = text.replace(n, "~")
        if "Legendary" in type_line:
            short = n.split(",")[0].strip()
            if short and short != n:
                text = text.replace(short, "~")
            first = n.split()[0]
            if len(n.split()) > 1 and len(first) > 3:
                text = re.sub(rf"\b{re.escape(first)}\b", "~", text)
    return text


def fmt_num(x):
    if x is None or (isinstance(x, float) and np.isnan(x)) or x == "":
        return ""
    try:
        f = float(x)
        return str(int(f)) if f.is_integer() else str(f)
    except (TypeError, ValueError):
        return str(x)


def build(fra_path: Path):
    d = pd.read_csv(FEAT)
    d = d[d["set"].str.upper().isin(RESEARCH_SETS)].copy()
    if set(d["set"].str.upper()) != RESEARCH_SETS:
        raise SystemExit("expected the 21 research sets")
    colors = lambda r: "".join(c for c in "WUBRG" if r.get("color_" + c, 0) == 1)
    rows = []
    for r in d.to_dict("records"):
        rows.append({"key": f"{r['set'].upper()}|{r['name']}", "name": r["name"], "type_line": r["type_line"] or "",
                     "text": r["oracle_text"] if isinstance(r["oracle_text"], str) else "",
                     "mv": fmt_num(r["mv"]), "colors": colors(r), "pt": f"{fmt_num(r['power'])}/{fmt_num(r['toughness'])}"})
    fra = json.loads(gzip.open(fra_path, "rt", encoding="utf-8").read())["cards"]
    for c in fra:
        rows.append({"key": f"FRA|{c['id']}", "name": c["name"], "type_line": gallery_to_scryfall(c.get("type_line")),
                     "text": gallery_to_scryfall(c.get("oracle_text")), "mv": fmt_num(c.get("cmc")),
                     "colors": "".join(c.get("colors") or []), "pt": f"{fmt_num(c.get('power'))}/{fmt_num(c.get('toughness'))}"})
    x = pd.DataFrame(rows)
    x["pt"] = x["pt"].where(x["pt"] != "/", "")
    x["btext"] = [blind(t, n, ty) for t, n, ty in zip(x["text"], x["name"], x["type_line"])]
    x["sig"] = x["btext"] + "␟" + x["type_line"] + "␟" + x["mv"] + "␟" + x["pt"]
    u = x.groupby("sig", sort=True).agg(keys=("key", lambda k: ";".join(sorted(k))), type_line=("type_line", "first"),
                                         btext=("btext", "first"), mv=("mv", "first"), colors=("colors", "first"),
                                         pt=("pt", "first")).reset_index(drop=True)
    u["auto"] = np.where(u["type_line"].str.contains("Basic Land") | (u["btext"].str.strip() == ""), 1, 0)
    rng = np.random.default_rng(SEED)
    u = u.iloc[rng.permutation(len(u))].reset_index(drop=True)
    u["id"] = np.arange(1, len(u) + 1)
    u.to_csv(OUT, index=False, compression="gzip")
    todo = int((u["auto"] == 0).sum())
    print({"rows": len(x), "unique": len(u), "auto_zero": int(u["auto"].sum()), "to_extract": todo,
           "batches": int(np.ceil(todo / BATCH))})


def show(n: int):
    u = pd.read_csv(OUT, keep_default_na=False)
    q = u[u["auto"] == 0].reset_index(drop=True)
    part = q.iloc[n * BATCH:(n + 1) * BATCH]
    for r in part.itertuples():
        head = f"#{r.id} | MV {r.mv} {r.colors or 'C'} | {r.type_line}" + (f" | {r.pt}" if r.pt else "")
        print(head + "\n" + r.btext.replace("\n", " / ") + "\n")
    print(f"-- batch {n}: ids {part['id'].min()}..{part['id'].max()}, {len(part)} cards")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fra", type=Path)
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    if a.show is not None:
        show(a.show)
    else:
        build(a.fra)
