#!/usr/bin/env python3
"""Probe which older sets have official 17Lands Public Game Data (metadata only; no outcomes are read).

HEAD-checks game_data_public.<SET>.<FORMAT>.csv.gz for pre-KHM sets and Arena remastered/flashback sets,
in Premier, Quick and Traditional Draft, and reads only the CSV header of Premier Draft files that exist.
"""
import csv
import gzip
import io
import json
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{}.{}.csv.gz"
OTHER = {"draft": "https://17lands-public.s3.amazonaws.com/analysis_data/draft_data/draft_data_public.{}.{}.csv.gz",
         "replay": "https://17lands-public.s3.amazonaws.com/analysis_data/replay_data/replay_data_public.{}.{}.csv.gz"}
OLD = ["M20", "ELD", "THB", "IKO", "M21", "ZNR", "AKR", "KLR", "KTK"]
SETS = ["KTK", "FRF", "DTK", "ORI", "BFZ", "OGW", "SOI", "EMN", "KLD", "AER", "AKH", "HOU", "XLN", "RIX", "DOM", "M19",
        "GRN", "RNA", "WAR", "M20", "ELD", "THB", "IKO", "M21", "ZNR", "AKR", "KLR", "SIR", "HBG", "YMID", "YNEO", "Y22",
        "LTR", "KTK", "OTP", "DSK", "PIO", "Cube", "CUBE"]
FORMATS = ["PremierDraft", "QuickDraft", "TradDraft"]
UA = {"User-Agent": "SakiyomiResearch/1.0"}


def head(code, fmt, base=BASE):
    try:
        req = urllib.request.Request(base.format(code, fmt), method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            return {"exists": True, "bytes": int(r.headers.get("Content-Length") or 0), "last_modified": r.headers.get("Last-Modified")}
    except urllib.error.HTTPError as e:
        return {"exists": False, "status": e.code}
    except Exception as e:  # noqa: BLE001
        return {"exists": False, "error": repr(e)[:200]}


def header(code, fmt):
    req = urllib.request.Request(BASE.format(code, fmt), headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        f = io.TextIOWrapper(gzip.GzipFile(fileobj=r), encoding="utf-8-sig", newline="")
        return next(csv.reader(f))


def main():
    out = {}
    for s in dict.fromkeys(SETS):
        out[s] = {}
        for fmt in FORMATS:
            h = head(s, fmt)
            if h.get("exists"):
                try:
                    cols = header(s, fmt)
                    h["n_columns"] = len(cols)
                    h["n_card_columns"] = sum(c.startswith("drawn_") for c in cols)
                    h["has_user_wr_bucket"] = "user_game_win_rate_bucket" in cols
                except Exception as e:  # noqa: BLE001
                    h["header_error"] = repr(e)[:200]
            out[s][fmt] = h
        print(s, {f: (v.get("exists"), v.get("bytes")) for f, v in out[s].items()}, flush=True)
    for kind, base in OTHER.items():
        for s in OLD:
            for fmt in FORMATS:
                h = head(s, fmt, base)
                out.setdefault(f"{kind}:{s}", {})[fmt] = h
            print(kind, s, {f: out[f"{kind}:{s}"][f].get("exists") for f in FORMATS}, flush=True)
    Path("research/older_sets").mkdir(parents=True, exist_ok=True)
    Path("research/older_sets/probe.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
