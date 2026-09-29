#!/usr/bin/env python3
"""Case 6 probe (metadata only, no outcomes are read).

- Lists Scryfall sets released after TDM and before FRA, excluding FIN / MH3 / FRA.
- HEAD-checks the official 17Lands Public Game Data (Premier Draft) file for each candidate and for the 21 research sets.
- Reads only the CSV header of each available file (to see whether user win-rate / n-games bucket columns exist).
- For two sets (one old, one recent) reads the two bucket columns from the first rows only, to choose top-player thresholds.
  No win/loss or card columns are read here.
"""
import csv
import gzip
import io
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

BASE = "https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{}.PremierDraft.csv.gz"
RESEARCH = ["KHM", "STX", "AFR", "MID", "VOW", "NEO", "SNC", "DMU", "BRO", "ONE", "MOM",
            "LTR", "WOE", "LCI", "MKM", "OTJ", "BLB", "DSK", "FDN", "DFT", "TDM"]
NEVER = {"FIN", "MH3", "FRA"}
AFTER, BEFORE = "2025-04-11", "2026-09-29"   # TDM release .. FRA release (exclusive)
UA = {"User-Agent": "SakiyomiResearch/1.0"}
OUT = Path("research/case6/probe.json")


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, "Accept": "application/json"}), timeout=60) as r:
        return json.load(r)


def head(code):
    try:
        req = urllib.request.Request(BASE.format(code), method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            return {"exists": True, "bytes": int(r.headers.get("Content-Length") or 0), "last_modified": r.headers.get("Last-Modified")}
    except urllib.error.HTTPError as e:
        return {"exists": False, "status": e.code}
    except Exception as e:  # noqa: BLE001
        return {"exists": False, "error": repr(e)[:200]}


def stream_rows(code, cols, max_rows):
    req = urllib.request.Request(BASE.format(code), headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        f = io.TextIOWrapper(gzip.GzipFile(fileobj=r), encoding="utf-8-sig", newline="")
        rd = csv.reader(f)
        header = next(rd)
        if not cols:
            return header, []
        idx = [header.index(c) for c in cols if c in header]
        rows = []
        for i, row in enumerate(rd):
            if i >= max_rows:
                break
            rows.append([row[j] for j in idx])
        return header, rows


def main():
    sets = get_json("https://api.scryfall.com/sets")["data"]
    cands = []
    for s in sets:
        code = s["code"].upper()
        if code in NEVER or s.get("digital"):
            continue
        if s.get("set_type") in ("expansion", "core", "draft_innovation") and AFTER < (s.get("released_at") or "") < BEFORE:
            cands.append({"code": code, "name": s["name"], "released_at": s["released_at"], "set_type": s["set_type"],
                          "card_count": s.get("card_count")})
    cands.sort(key=lambda x: x["released_at"])
    out = {"window": [AFTER, BEFORE], "candidates": [], "research": {}, "bucket_samples": {}}
    for c in cands:
        c["public_game_data"] = head(c["code"])
        if c["public_game_data"]["exists"]:
            h, _ = stream_rows(c["code"], [], 0)
            c["n_columns"] = len(h)
            c["has_user_wr_bucket"] = "user_game_win_rate_bucket" in h
            c["has_user_n_games_bucket"] = "user_n_games_bucket" in h
            c["meta_columns"] = [x for x in h if not x.split("_")[0] in ("deck", "sideboard", "drawn", "tutored", "opening")][:60]
        out["candidates"].append(c)
        print(c["code"], c["released_at"], c["public_game_data"].get("exists"), flush=True)
    for code in RESEARCH:
        info = head(code)
        if info["exists"]:
            h, _ = stream_rows(code, [], 0)
            info["has_user_wr_bucket"] = "user_game_win_rate_bucket" in h
            info["has_user_n_games_bucket"] = "user_n_games_bucket" in h
        out["research"][code] = info
        print(code, info.get("has_user_wr_bucket"), flush=True)
    avail = [c["code"] for c in out["candidates"] if c["public_game_data"]["exists"] and c.get("has_user_wr_bucket")]
    for code in ["KHM", "TDM"] + avail[-1:]:
        cols = ["user_game_win_rate_bucket", "user_n_games_bucket"]
        _, rows = stream_rows(code, cols, 300000)
        wr = Counter(r[0] for r in rows)
        ng = Counter(r[1] for r in rows) if rows and len(rows[0]) > 1 else Counter()
        out["bucket_samples"][code] = {"rows": len(rows), "user_game_win_rate_bucket": dict(sorted(wr.items())),
                                       "user_n_games_bucket": dict(sorted(ng.items()))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    sys.exit(main())
