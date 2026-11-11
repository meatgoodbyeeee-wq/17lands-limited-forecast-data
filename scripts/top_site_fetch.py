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


# Request variants. The first run showed that card_ratings/data with start_date/end_date returns
# zero game counts for past sets, so the endpoint and the group parameter are probed on one set first.
BASES = {
    "ratings_nodates": lambda s, a, b: (BASE, {"expansion": s, "format": "PremierDraft"}),
    "api_alltime": lambda s, a, b: ("https://www.17lands.com/api/card_data", {"expansion": s, "event_type": "PremierDraft", "time_period": "ALL_TIME"}),
    "ratings_dates": lambda s, a, b: (BASE, {"expansion": s, "format": "PremierDraft", "start_date": a, "end_date": b}),
}
GROUP_PARAMS = [("user_group", "top"), ("user_group", "Top"), ("player_group", "top")]


def build_url(set_code, start, end, group, base="ratings_dates", group_param=("user_group", "top")):
    url, q = BASES[base](set_code, start, end)
    if group:
        q[group_param[0]] = group_param[1]
    return url + "?" + urllib.parse.urlencode(q)


def total_games(cards):
    return sum((c.get("ever_drawn_game_count") or 0) for c in cards.values())


def probe(set_code, start, end, getter, pause=8, retry_wait=30):
    """Try each endpoint / group-parameter variant on one set. Returns (log, chosen variant or None)."""
    log, chosen = [], None
    for base in BASES:
        info, all_cards = fetch_one(build_url(set_code, start, end, None, base), getter, wait=retry_wait)
        info.update({"probe": True, "set": set_code, "base": base, "group": "all", "gih_games": total_games(all_cards)})
        log.append(info); print("probe", base, "all", info["status"], info["rows"], info["gih_games"], info["error"], flush=True)
        time.sleep(pause)
        if not total_games(all_cards):
            continue
        for gp in GROUP_PARAMS:
            info, top_cards = fetch_one(build_url(set_code, start, end, "top", base, gp), getter, wait=retry_wait)
            share = total_games(top_cards) / total_games(all_cards)
            info.update({"probe": True, "set": set_code, "base": base, "group": f"{gp[0]}={gp[1]}", "gih_games": total_games(top_cards), "share_of_all": share})
            log.append(info); print("probe", base, gp, info["status"], info["rows"], info["gih_games"], round(share, 4), info["error"], flush=True)
            time.sleep(pause)
            if chosen is None and 0.01 < share < 0.95:
                chosen = {"base": base, "group_param": list(gp)}
                break
        if chosen:
            break
    return log, chosen


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


def run(sets, data_dir, getter=http_get, pause=8, retry_wait=30, probe_set=None):
    log, rows = [], []
    for s in sets:
        if s in REFUSED:
            raise SystemExit(f"Refusing {s}")
    ps = probe_set or sets[0]
    man = json.loads((Path(data_dir) / f"{ps}_case6_manifest.json").read_text())
    plog, chosen = probe(ps, *window_dates(man), getter, pause=pause, retry_wait=retry_wait)
    log.extend(plog)
    print("chosen variant", chosen, flush=True)
    if not chosen:
        return log, rows, None
    for s in sets:
        man = json.loads((Path(data_dir) / f"{s}_case6_manifest.json").read_text())
        start, end = window_dates(man)
        got = {}
        for group in (None, "top"):
            info, cards = fetch_one(build_url(s, start, end, group, chosen["base"], tuple(chosen["group_param"])), getter, wait=retry_wait)
            info.update({"set": s, "group": group or "all", "start_date": start, "end_date": end, "gih_games": total_games(cards)})
            log.append(info); got[group or "all"] = cards
            print(s, group or "all", info["status"], info["rows"], info["gih_games"], info["error"], flush=True)
            time.sleep(pause)
        log[-1]["user_group_ignored"] = same_response(got["all"], got["top"])
        rows.extend(merge(s, got["all"], got["top"]))
    return log, rows, chosen


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
    log, rows, chosen = run(sets, a.data_dir, probe_set="MKM" if "MKM" in sets else None)
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    for r in log:
        r["keys"] = r["keys"][:0] if r is not log[0] else r["keys"]  # keep the field list once
    (out / "fetch_log.json").write_text(json.dumps({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "chosen_variant": chosen, "requests": log}, indent=1))
    old = out / "site_top_cards.csv"
    if old.exists():
        old.unlink()  # the first run's file held only zero counts
    if rows:
        with open(out / "site_top_cards.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    ok = sum(1 for r in log if r["status"] == 200 and r["rows"] and r.get("gih_games"))
    print(f"requests ok {ok}/{len(log)}, card rows {len(rows)}")


if __name__ == "__main__":
    main()
