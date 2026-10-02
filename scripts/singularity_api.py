#!/usr/bin/env python3
"""Early-window card and colour ratings for PAST sets from the same 17Lands endpoints the website uses.

Why: the FRA numbers in the article come from card_ratings/data and color_ratings/data. Fetching the same
fields for past sets over the same early window (first 3 days) gives an apples-to-apples comparison and reaches
back to sets whose Public Game Data is not published. FRA is refused here: it is outside the embargo until 2026-10-13.

For every set it stores raw JSON for start..start+k with the end date both inclusive and exclusive variants,
so the matching convention can be checked against the Public Game Data afterwards.
"""
import argparse
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REFUSE = {"FRA", "MH3"}
UA = {"User-Agent": "SakiyomiResearch/1.0", "Accept": "application/json"}
BASE = "https://www.17lands.com"


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404):
                raise
            err = e
        except Exception as e:
            err = e
        time.sleep(5 * (k + 1))
    raise err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--sleep", type=float, default=1.5)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    filters = get(f"{BASE}/data/filters")
    starts = filters.get("start_dates", {})
    log = {}
    for s in [x.upper() for x in a.sets]:
        if s in REFUSE:
            continue
        if s not in starts:
            log[s] = "no start date"
            continue
        d0 = dt.date.fromisoformat(starts[s][:10])
        variants = {"W1a": (0, 0), "W1b": (0, 1), "W3a": (0, 2), "W3b": (0, 3)}
        for name, (lo, hi) in variants.items():
            q = {"expansion": s, "start_date": (d0 + dt.timedelta(days=lo)).isoformat(),
                 "end_date": (d0 + dt.timedelta(days=hi)).isoformat()}
            todo = [("colors", f"{BASE}/color_ratings/data?" + urllib.parse.urlencode(
                {**q, "event_type": "PremierDraft", "combine_splash": "false"}))]
            if name.startswith("W3"):
                todo.append(("cards", f"{BASE}/card_ratings/data?" + urllib.parse.urlencode({**q, "format": "PremierDraft"})))
            for kind, url in todo:
                path = a.out_dir / f"{s}_{kind}_{name}.json"
                try:
                    data = get(url)
                    path.write_text(json.dumps(data))
                    log[f"{s}/{kind}/{name}"] = len(data)
                except Exception as e:
                    log[f"{s}/{kind}/{name}"] = f"ERR {e!r}"
                time.sleep(a.sleep)
        print(s, {k: v for k, v in log.items() if k.startswith(s + "/")}, flush=True)
    (a.out_dir / "_log.json").write_text(json.dumps({"starts": {k: starts[k] for k in starts if k in {x.upper() for x in a.sets}}, "log": log}, indent=1))


if __name__ == "__main__":
    main()
