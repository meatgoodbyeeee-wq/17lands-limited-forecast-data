#!/usr/bin/env python3
"""Skill comparison, site side: 17Lands card data for the site's player groups (all, top, middle, bottom) on past sets,
plus mana value and type line from Scryfall's oracle bulk file.

The site groups are assigned from players' results in earlier formats (not from the games counted), so they are the
comparison without the selection-on-outcome of the public-data win-rate bucket.
Endpoint: https://www.17lands.com/api/card_data?expansion=<SET>&event_type=PremierDraft&time_period=ALL_TIME[&user_group=<g>]
FRA, TRK, FIN and MH3 are refused. One request per set and group, spaced out.
Usage: python3 skill_site_fetch.py --sets AFR BLB ... --out-dir research/top_player/skill_compare/data
"""
import argparse, csv, gzip, io, json, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

API = "https://www.17lands.com/api/card_data"
REFUSED = {"FRA", "TRK", "FIN", "MH3"}
GROUPS = [None, "top", "middle", "bottom"]
DROP = {"url", "url_back"}
UA = {"User-Agent": "SakiyomiResearch/1.0", "Accept": "application/json"}


def http_get(url, timeout=180):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.status, r.read()


def fetch_group(s, g, getter, retry_wait=30):
    q = {"expansion": s, "event_type": "PremierDraft", "time_period": "ALL_TIME"}
    if g:
        q["user_group"] = g
    url = API + "?" + urllib.parse.urlencode(q)
    err = None
    for attempt in range(2):
        try:
            st, body = getter(url)
            x = json.loads(body)
            rows = x.get("data", x) if isinstance(x, dict) else x
            return {"set": s, "group": g or "all", "url": url, "status": st, "rows": len(rows), "error": None}, rows
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
        except Exception as e:
            err = repr(e)[:300]
        if attempt == 0:
            time.sleep(retry_wait)
    return {"set": s, "group": g or "all", "url": url, "status": None, "rows": 0, "error": err}, []


def scryfall_oracle(getter):
    st, body = getter("https://api.scryfall.com/bulk-data/oracle-cards")
    uri = json.loads(body)["download_uri"]
    st, body = getter(uri)
    out = {}
    for c in json.loads(body):
        faces = c.get("card_faces") or []
        rec = {"mv": c.get("cmc"), "type_line": c.get("type_line") or (faces[0].get("type_line") if faces else None),
               "colors": "".join(c.get("colors") or (faces[0].get("colors") if faces else []) or [])}
        names = [c.get("name", "")] + [f.get("name", "") for f in faces]
        for n in names:
            if n and n not in out:
                out[n] = rec
    return out


def run(sets, out_dir, getter=http_get, pause=8, retry_wait=30, oracle_getter=None):
    for s in sets:
        if s in REFUSED:
            raise SystemExit(f"Refusing {s}")
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    log, rows = [], []
    for s in sets:
        totals = {}
        for g in GROUPS:
            info, data = fetch_group(s, g, getter, retry_wait)
            info["gih_games"] = sum((r.get("ever_drawn_game_count") or 0) for r in data)
            totals[info["group"]] = info["gih_games"]
            log.append(info)
            print(s, info["group"], info["status"], info["rows"], info["gih_games"], info["error"], flush=True)
            for r in data:
                rr = {k: v for k, v in r.items() if k not in DROP and not isinstance(v, (dict, list))}
                rr["set"] = s; rr["group"] = info["group"]
                rows.append(rr)
            time.sleep(pause)
        a = totals.get("all") or 0
        for r in log[-len(GROUPS):]:
            r["share_of_all"] = (r["gih_games"] / a) if a else None
            r["group_ignored"] = bool(a) and r["group"] != "all" and r["gih_games"] == a
    keys = sorted({k for r in rows for k in r})
    with gzip.open(out_dir / "site_groups.csv.gz", "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["set", "group"] + [k for k in keys if k not in ("set", "group")]); w.writeheader(); w.writerows(rows)
    meta = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "requests": log}
    try:
        orc = scryfall_oracle(oracle_getter or getter)
        names = sorted({(r["set"], r["name"]) for r in rows if r.get("name")})
        with gzip.open(out_dir / "card_scryfall.csv.gz", "wt", newline="") as fh:
            w = csv.writer(fh); w.writerow(["set", "name", "mv", "type_line", "colors", "matched"])
            hit = 0
            for s, n in names:
                rec = orc.get(n) or orc.get(n.split(" // ")[0])
                hit += bool(rec)
                w.writerow([s, n, rec["mv"] if rec else "", rec["type_line"] if rec else "", rec["colors"] if rec else "", int(bool(rec))])
        meta["scryfall"] = {"names": len(names), "matched": hit}
    except Exception as e:
        meta["scryfall"] = {"error": repr(e)[:300]}
    (out_dir / "site_fetch_log.json").write_text(json.dumps(meta, indent=1))
    ok = sum(1 for r in log if r["status"] == 200 and r["rows"])
    print(f"requests ok {ok}/{len(log)}; scryfall {meta['scryfall']}")
    return log, rows, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    run([s.upper() for s in a.sets], a.out_dir)


if __name__ == "__main__":
    main()
