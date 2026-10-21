#!/usr/bin/env python3
"""C3 extraction pipeline for ONE not-yet-released set (e.g. TRK), using the same rubric, blinding and features as production.

Everything for a set lives in research/newset/<SET>/ :  cards.csv.gz (blinded queue), raw/b*.txt (extractor output), c3_features.csv.gz.
Nothing here reads 17Lands outcomes, FIN or MH3, and nothing touches research/gih_llm_extract (the production C3 files).

  python newset.py queue    --set TRK --cards <set card file: target.json.gz schema>   # card file -> blinded queue
  python newset.py show     --set TRK 0                                                # print blinded batch 0 for the extractor
  python newset.py check    --set TRK [--missing]                                      # validate raw/b*.txt against the queue
  python newset.py features --set TRK                                                  # raw -> c3_features.csv.gz (keys "<SET>|<card id>")

The rubric is research/gih_llm_extract/RUBRIC.md and is used unchanged. The extractor sees only mana value, colours, type line,
P/T and rules text with the card name replaced by "~" (set, rarity and every number hidden); ids are shuffled with a fixed seed.
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research/gih_llm_extract"))
sys.path.insert(0, str(ROOT / "scripts"))
import build_input as bi  # noqa: E402  (gallery_to_scryfall, blind, fmt_num, BATCH)
import c3_research as c3  # noqa: E402  (FIELDS, MAX, DEPS, LINE, c3_columns)

FORBIDDEN = {"FIN", "MH3"}
SEED = 20260929  # same shuffle seed as production C3


def sdir(code: str) -> Path:
    code = code.upper()
    if code in FORBIDDEN:
        raise SystemExit(f"{code} is reserved and must not be used")
    return HERE / code


def cmd_queue(a):
    code = a.set.upper()
    d = sdir(code)
    cards = json.loads(gzip.open(a.cards, "rt", encoding="utf-8").read())["cards"]
    if not cards:
        raise SystemExit("card file has no cards")
    rows = []
    for c in cards:
        rows.append({"key": f"{code}|{c['id']}", "name": c["name"], "type_line": bi.gallery_to_scryfall(c.get("type_line")),
                     "text": bi.gallery_to_scryfall(c.get("oracle_text")), "mv": bi.fmt_num(c.get("cmc")),
                     "colors": "".join(c.get("colors") or []), "pt": f"{bi.fmt_num(c.get('power'))}/{bi.fmt_num(c.get('toughness'))}"})
    x = pd.DataFrame(rows)
    x["pt"] = x["pt"].where(x["pt"] != "/", "")
    x["btext"] = [bi.blind(t, n, ty) for t, n, ty in zip(x["text"], x["name"], x["type_line"])]
    x["sig"] = x["btext"] + "␟" + x["type_line"] + "␟" + x["mv"] + "␟" + x["pt"]
    u = x.groupby("sig", sort=True).agg(keys=("key", lambda k: ";".join(sorted(k))), type_line=("type_line", "first"),
                                         btext=("btext", "first"), mv=("mv", "first"), colors=("colors", "first"),
                                         pt=("pt", "first")).reset_index(drop=True)
    u["auto"] = np.where(u["type_line"].str.contains("Basic Land") | (u["btext"].str.strip() == ""), 1, 0)
    rng = np.random.default_rng(SEED)
    u = u.iloc[rng.permutation(len(u))].reset_index(drop=True)
    u["id"] = np.arange(1, len(u) + 1)
    d.mkdir(parents=True, exist_ok=True)
    (d / "raw").mkdir(exist_ok=True)
    out = d / "cards.csv.gz"
    if out.exists() and not a.force:
        old = pd.read_csv(out, keep_default_na=False)
        if (old["btext"].tolist() != u["btext"].tolist()) and any((d / "raw").glob("b*.txt")):
            raise SystemExit("queue would change while raw/ already holds extractions; rerun with --force only after removing raw/")
    u.to_csv(out, index=False, compression="gzip")
    todo = int((u["auto"] == 0).sum())
    print(json.dumps({"set": code, "cards": len(x), "unique": len(u), "auto_zero": int(u["auto"].sum()), "to_extract": todo,
                      "batches": int(np.ceil(todo / bi.BATCH))}))


def queue_of(code: str) -> pd.DataFrame:
    return pd.read_csv(sdir(code) / "cards.csv.gz", keep_default_na=False)


def cmd_show(a):
    q = queue_of(a.set)
    q = q[q["auto"] == 0].reset_index(drop=True)
    part = q.iloc[a.batch * bi.BATCH:(a.batch + 1) * bi.BATCH]
    for r in part.itertuples():
        head = f"#{r.id} | MV {r.mv} {r.colors or 'C'} | {r.type_line}" + (f" | {r.pt}" if r.pt else "")
        print(head + "\n" + r.btext.replace("\n", " / ") + "\n")
    print(f"-- batch {a.batch}: ids {part['id'].min()}..{part['id'].max()}, {len(part)} cards")


def load_raw(code: str):
    out, errors = {}, []
    for f in sorted((sdir(code) / "raw").glob("b*.txt")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            m = c3.LINE.match(line.strip())
            if not m:
                errors.append(f"{f.name}:{n} bad format: {line!r}")
                continue
            i, digits, dep = int(m.group(1)), m.group(2), m.group(3)
            vals = [int(ch) for ch in digits]
            if any(v > mx for v, mx in zip(vals, c3.MAX)):
                errors.append(f"{f.name}:{n} out of range: {line}")
            if dep not in "-" + "".join(c3.DEPS):
                errors.append(f"{f.name}:{n} bad dep: {line}")
            if i in out:
                errors.append(f"{f.name}:{n} duplicate id {i}")
            out[i] = vals + [dep]
    return out, errors


def cmd_check(a):
    q = queue_of(a.set)
    raw, errors = load_raw(a.set)
    todo = set(q.loc[q["auto"] == 0, "id"])
    extra, missing = sorted(set(raw) - todo), sorted(todo - set(raw))
    for e in errors[:50]:
        print(e)
    print(f"annotated {len(raw)} / {len(todo)}; errors {len(errors)}; ids not in queue {extra[:20]}")
    if a.missing:
        qq = q[q["auto"] == 0].reset_index(drop=True)
        pos = {i: k // bi.BATCH for k, i in enumerate(qq["id"])}
        by = {}
        for i in missing:
            by.setdefault(pos[i], []).append(i)
        print({b: len(v) for b, v in sorted(by.items())})
    if errors or extra or missing:
        raise SystemExit(1)


def cmd_features(a):
    code = a.set.upper()
    raw, errors = load_raw(code)
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    u = queue_of(code)
    todo = set(u.loc[u["auto"] == 0, "id"])
    if set(raw) != todo:
        raise SystemExit(f"coverage mismatch: missing {len(todo - set(raw))}, extra {len(set(raw) - todo)}")
    rows = []
    for r in u.itertuples():
        if r.auto:  # basic lands and cards with no rules text: zeros, except a vanilla creature is one body (same as production)
            vals = [0] * 10 + ["-"]
            if "Creature" in r.type_line:
                vals[2] = 1
        else:
            vals = raw[r.id]
        for key in r.keys.split(";"):
            rows.append([key, r.id, r.auto, r.mv] + vals)
    x = pd.DataFrame(rows, columns=["key", "id", "auto", "mv"] + c3.FIELDS + ["dep"])
    if x["key"].duplicated().any():
        raise SystemExit("a key maps to two extraction rows")
    feats = c3.c3_columns(x, x["mv"])
    out = pd.concat([x[["key", "id", "auto"]], x[c3.FIELDS + ["dep"]], feats], axis=1)
    out.to_csv(sdir(code) / "c3_features.csv.gz", index=False, compression="gzip")
    print(json.dumps({"set": code, "keys": len(out), "unique_rows": int(out["id"].nunique()),
                      "auto_rows": int(out.loc[out.auto == 1, "id"].nunique())}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("queue"); p.add_argument("--set", required=True); p.add_argument("--cards", type=Path, required=True)
    p.add_argument("--force", action="store_true"); p.set_defaults(f=cmd_queue)
    p = sub.add_parser("show"); p.add_argument("--set", required=True); p.add_argument("batch", type=int); p.set_defaults(f=cmd_show)
    p = sub.add_parser("check"); p.add_argument("--set", required=True); p.add_argument("--missing", action="store_true")
    p.set_defaults(f=cmd_check)
    p = sub.add_parser("features"); p.add_argument("--set", required=True); p.set_defaults(f=cmd_features)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
