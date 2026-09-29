#!/usr/bin/env python3
"""Blind C3 extraction queue for the case-6 new sets (same procedure as research/gih_llm_extract).

Reads only data/new_cards_text.csv.gz (no outcome columns). Texts already extracted in case 1 are reused by signature.

  python c3_queue.py build        # -> c3_cards_new.csv.gz
  python c3_queue.py --show N     # print batch N (blinded)
  python c3_queue.py check        # validate c3_raw/*.txt coverage
  python c3_queue.py features     # -> c3_features_new.csv.gz (one row per SET|name, new sets)
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EXT = HERE.parent / "gih_llm_extract"
sys.path.insert(0, str(EXT))
from build_input import blind, fmt_num  # noqa: E402
import c3_research as c3  # noqa: E402

TEXT = HERE / "data/new_cards_text.csv.gz"
OUT = HERE / "c3_cards_new.csv.gz"
RAW = HERE / "c3_raw"
SEED = 20260930
BATCH = 150
START_ID = 10001
REFUSE = {"FIN", "MH3", "FRA"}


def sig(btext, type_line, mv, pt):
    return f"{btext}␟{type_line}␟{mv}␟{pt}"


def build():
    t = pd.read_csv(TEXT, keep_default_na=False)
    if set(t["set"].str.upper()) & REFUSE:
        raise SystemExit("refused set present")
    t["type_line"] = t["type_line"].astype(str)
    t["text"] = t["oracle_text"].astype(str)
    t["mv"] = [fmt_num(x) for x in t["mv"]]
    t["pt"] = [f"{fmt_num(p)}/{fmt_num(q)}" for p, q in zip(t["power"], t["toughness"])]
    t["pt"] = t["pt"].where(t["pt"] != "/", "")
    t["colors"] = ["".join(c for c in "WUBRG" if str(r[f"color_{c}"]) in ("1", "1.0")) for _, r in t.iterrows()]
    t["btext"] = [blind(x, n, ty) for x, n, ty in zip(t["text"], t["name"], t["type_line"])]
    t["key"] = t["set"].str.upper() + "|" + t["name"]
    t["sig"] = [sig(*v) for v in zip(t["btext"], t["type_line"], t["mv"], t["pt"])]
    old = pd.read_csv(EXT / "cards.csv.gz", keep_default_na=False)
    old["sig"] = [sig(*v) for v in zip(old["btext"], old["type_line"], old["mv"].astype(str), old["pt"])]
    old_map = dict(zip(old["sig"], old["id"]))
    u = t.groupby("sig", sort=True).agg(keys=("key", lambda k: ";".join(sorted(k))), type_line=("type_line", "first"),
                                         btext=("btext", "first"), mv=("mv", "first"), colors=("colors", "first"),
                                         pt=("pt", "first")).reset_index()
    u["reuse_id"] = u["sig"].map(old_map)
    u["auto"] = np.where(u["type_line"].str.contains("Basic Land") | (u["btext"].str.strip() == ""), 1, 0)
    rng = np.random.default_rng(SEED)
    u = u.iloc[rng.permutation(len(u))].reset_index(drop=True)
    u["id"] = np.arange(START_ID, START_ID + len(u))
    u = u.drop(columns=["sig"])
    u.to_csv(OUT, index=False, compression="gzip")
    todo = u[(u["auto"] == 0) & u["reuse_id"].isna()]
    print({"rows": len(t), "unique": len(u), "reused": int(u["reuse_id"].notna().sum()), "auto": int(u["auto"].sum()),
           "to_extract": len(todo), "batches": int(np.ceil(len(todo) / BATCH))})


def queue():
    u = pd.read_csv(OUT, keep_default_na=False)
    return u[(u["auto"] == 0) & (u["reuse_id"] == "")].reset_index(drop=True)


def show(n):
    part = queue().iloc[n * BATCH:(n + 1) * BATCH]
    for r in part.itertuples():
        head = f"#{r.id} | MV {r.mv} {r.colors or 'C'} | {r.type_line}" + (f" | {r.pt}" if r.pt else "")
        print(head + "\n" + r.btext.replace("\n", " / ") + "\n")
    print(f"-- batch {n}: ids {part['id'].min()}..{part['id'].max()}, {len(part)} cards")


def read_raw():
    out = {}
    for f in sorted(RAW.glob("n*.txt")):
        for ln in f.read_text().splitlines():
            if not ln.strip():
                continue
            m = c3.LINE.match(ln.strip())
            if not m:
                raise SystemExit(f"bad line in {f.name}: {ln!r}")
            d = [int(x) for x in m.group(2)]
            if any(v > mx for v, mx in zip(d, c3.MAX)) or m.group(3) not in "-" + "".join(c3.DEPS):
                raise SystemExit(f"out of range in {f.name}: {ln!r}")
            if int(m.group(1)) in out:
                raise SystemExit(f"duplicate {m.group(1)}")
            out[int(m.group(1))] = d + [m.group(3)]
    return out


def check():
    raw = read_raw()
    want = set(queue()["id"])
    print({"annotated": len(raw), "want": len(want), "missing": len(want - set(raw)), "extra": len(set(raw) - want)})


def features():
    raw = read_raw()
    old = c3.read_raw()
    u = pd.read_csv(OUT, keep_default_na=False)
    rows = []
    for r in u.itertuples():
        if r.auto:
            vals = [0] * 10 + ["-"]
            if "Creature" in r.type_line:
                vals[2] = 1
        elif r.reuse_id != "":
            vals = old[int(float(r.reuse_id))]
        else:
            vals = raw[r.id]
        for key in r.keys.split(";"):
            rows.append([key, r.id, r.auto, r.mv] + list(vals))
    x = pd.DataFrame(rows, columns=["key", "id", "auto", "mv"] + c3.FIELDS + ["dep"])
    feats = c3.c3_columns(x, x["mv"])
    out = pd.concat([x[["key", "id", "auto"]], x[c3.FIELDS + ["dep"]], feats], axis=1)
    out.to_csv(HERE / "c3_features_new.csv.gz", index=False, compression="gzip")
    print({"keys": len(out)})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=["build", "check", "features"])
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    if a.show is not None:
        show(a.show)
    else:
        {"build": build, "check": check, "features": features}[a.cmd]()
