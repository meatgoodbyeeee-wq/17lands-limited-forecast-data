#!/usr/bin/env python3
"""Fetch 17Lands site card ratings (all users and the site's "top" user group) for past sets.

Purpose: check whether the public-data top-player aggregate of Case 6 (top60n50) agrees with the
"Top" user-group filter on the 17Lands card data page. Past sets only (Public Game Data released);
FRA and TRK are refused. Two requests per set (all users, user_group=top), spaced out.
Only the fields needed for the comparison are kept.
"""
import argparse, csv, json, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://www.17lands.com/card_ratings/data"
REFUSED = {"FRA", "TRK", "FIN", "MH3"}
FIELDS = ["game_count", "win_rate", "ever_drawn_game_count", "ever_drawn_win_rate"]


def window_dates(manifest):
    """Calendar dates covering the Case 6 28-day window (start day .. end day, inclusive)."""
    return manifest["window_start"][:10], manifest["window_end"][:10]


def build_url(set_code, start, end, group):
    q = {"expansion": set_code, "format": "PremierDraft", "start_date": start, "end_date": end}
    if group:
        q["user_group"] = group
    return BASE + "?" + urllib.parse.urlencode(q)


def http_get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "LimitedForecastResearch/2.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8")


def parse(text):
    x = json.loads(text)
    rows = x.get("data", x) if isinstance(x, dict) else x
    out = {}
    for c in rows:
        name = c.get("name")
        if not name:
            continue
        out[name] = {k: c.get(k) for k in FIELDS}
    keys = sorted(rows[0].keys()) if rows else []
    return out, keys


def fetch_one(url, getter, retries=1, wait=30):
    last = None
    for attempt in range(retries + 1):
        try:
            status, text = getter(url)
            cards, keys = parse(text)
            return {"url": url, "status": status, "rows": len(cards), "keys": keys, "error": None}, cards
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # network, JSON
            last = repr(e)[:300]
        if attempt < retries:
            time.sleep(wait)
    return {"url": url, "status": None, "rows": 0, "keys": [], "error": last}, {}


def merge(set_code, all_cards, top_cards):
    rows = []
    for name in sorted(set(all_cards) | set(top_cards)):
        a, t = all_cards.get(name, {}), top_cards.get(name, {})
        rows.append({"set": set_code, "name": name,
                     "all_gp_n": a.get("game_count"), "all_gp_wr": a.get("win_rate"),
                     "all_gih_n": a.get("ever_drawn_game_count"), "all_gih_wr": a.get("ever_drawn_win_rate"),
                     "top_gp_n": t.get("game_count"), "top_gp_wr": t.get("win_rate"),
                     "top_gih_n": t.get("ever_drawn_game_count"), "top_gih_wr": t.get("ever_drawn_win_rate")})
    return rows


def same_response(all_cards, top_cards):
    """True if the user_group parameter had no effect (identical GIH counts)."""
    if not all_cards or not top_cards:
        return False
    common = set(all_cards) & set(top_cards)
    return bool(common) and all(all_cards[n]["ever_drawn_game_count"] == top_cards[n]["ever_drawn_game_count"] for n in common)


def run(sets, data_dir, getter=http_get, pause=8, retry_wait=30):
    log, rows = [], []
    for s in sets:
        if s in REFUSED:
            raise SystemExit(f"Refusing {s}")
        man = json.loads((Path(data_dir) / f"{s}_case6_manifest.json").read_text())
        start, end = window_dates(man)
        got = {}
        for group in (None, "top"):
            info, cards = fetch_one(build_url(s, start, end, group), getter, wait=retry_wait)
            info.update({"set": s, "group": group or "all", "start_date": start, "end_date": end})
            log.append(info); got[group or "all"] = cards
            print(s, group or "all", info["status"], info["rows"], info["error"], flush=True)
            time.sleep(pause)
        ignored = same_response(got["all"], got["top"])
        log[-1]["user_group_ignored"] = ignored
        rows.extend(merge(s, got["all"], got["top"]))
    return log, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="research/case6/data")
    ap.add_argument("--out-dir", default="research/top_player/site_top")
    ap.add_argument("--sets", nargs="*")
    a = ap.parse_args()
    if a.sets:
        sets = [s.upper() for s in a.sets]
    else:
        sets = []
        for f in sorted(Path(a.data_dir).glob("*_case6_manifest.json")):
            m = json.loads(f.read_text())
            if m.get("has_user_wr_bucket"):
                sets.append(m["set"])
    log, rows = run(sets, a.data_dir)
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "fetch_log.json").write_text(json.dumps({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "requests": log}, indent=1))
    if rows:
        with open(out / "site_top_cards.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    ok = sum(1 for r in log if r["status"] == 200 and r["rows"])
    print(f"requests ok {ok}/{len(log)}, card rows {len(rows)}")


if __name__ == "__main__":
    main()
