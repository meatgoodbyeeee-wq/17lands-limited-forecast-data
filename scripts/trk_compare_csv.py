#!/usr/bin/env python3
"""Joins the published TRK forecast with the 17Lands Card Data snapshot for the private comparison page.

  python3 scripts/trk_compare_csv.py --forecast <forecast-trk.json> --images <pages>/data/trk/card-images.json \
      --live live/trk-card-data.json --out <dir>

forecast-trk.json is what the site publishes (built with `node scripts/build-set-forecast.mjs TRK --out ...` in the Pages
repository; GIH WR, its 80% range and ALSA are the pre-release forecast). Writes <dir>/trk_compare.csv (one row per card)
and <dir>/trk_snapshot.csv (one row: where and when the observed values come from). Prints names it could not match.
Nothing here changes a forecast.
"""
import argparse, csv, json, re, unicodedata
from pathlib import Path


def norm(s):
    s = unicodedata.normalize('NFKC', str(s or ''))
    s = re.sub(r"[‘’ʼ`´]", "'", s).replace('“', '"').replace('”', '"')
    s = re.sub(r'\s*//?\s*', ' // ', s)
    return re.sub(r'\s+', ' ', s).strip().lower()


def colour(c):
    cs = c.get('colors') or []
    return 'multi' if len(cs) > 1 else (cs[0] if cs else 'colorless')


def kind(c):
    t = (c.get('type_line') or '').lower()
    if 'land' in t and 'creature' not in t:
        return 'land'
    if 'creature' in t:
        return 'creature'
    if 'instant' in t or 'sorcery' in t:
        return 'instant/sorcery'
    return 'other'


def num(v, lo=None, hi=None):
    if not isinstance(v, (int, float)) or v != v:
        return None
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        return None
    return float(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--forecast', required=True); ap.add_argument('--images', required=True)
    ap.add_argument('--live', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    f = json.load(open(a.forecast))['forecast']
    ja = json.load(open(a.images))
    live = json.load(open(a.live))
    cards = f['cards']
    by, dup = {}, set()
    for c in cards:
        for k in {norm(c['name']), norm(c['name'].split('//')[0])}:
            if k in by and by[k]['id'] != c['id']:
                dup.add(k)
            by.setdefault(k, c)
    obs, unmatched = {}, []
    for r in live['cards']:
        k, front = norm(r.get('name')), norm(str(r.get('name') or '').split('//')[0])
        c = by.get(k) if k in by and k not in dup else by.get(front) if front in by and front not in dup else None
        if c is None:
            unmatched.append(r.get('name')); continue
        obs.setdefault(c['id'], r)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cols = ['id', 'name', 'name_ja', 'rarity', 'color', 'type', 'cmc', 'pred_gih', 'pred_lo', 'pred_hi', 'pred_alsa',
            'obs_gih', 'gih_n', 'obs_alsa', 'seen_n', 'gih_diff', 'in_range']
    rows = []
    for c in cards:
        r = obs.get(c['id'], {})
        g = num(r.get('ever_drawn_win_rate'), 0, 1)
        gn = int(r.get('ever_drawn_game_count') or 0)
        al = num(r.get('avg_seen'), 1, 15)
        lo, hi = c['gih_range']
        og = round(g * 100, 2) if g is not None and gn > 0 else None
        rows.append({'id': c['id'], 'name': c['name'], 'name_ja': (ja.get(c['id']) or {}).get('name_ja') or '',
                     'rarity': c.get('rarity'), 'color': colour(c), 'type': kind(c), 'cmc': c.get('cmc'),
                     'pred_gih': round(c['gih'], 2), 'pred_lo': round(lo, 2), 'pred_hi': round(hi, 2), 'pred_alsa': round(c['alsa'], 2),
                     'obs_gih': og, 'gih_n': gn, 'obs_alsa': round(al, 2) if al is not None and (r.get('seen_count') or 0) > 0 else None,
                     'seen_n': int(r.get('seen_count') or 0),
                     'gih_diff': round(og - c['gih'], 2) if og is not None else None,
                     'in_range': '' if og is None else ('yes' if lo <= og <= hi else 'no')})
    with open(out / 'trk_compare.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for r in rows:
            w.writerow({k: ('' if r[k] is None else r[k]) for k in cols})
    snap = {'source': live.get('attribution'), 'source_url': live.get('source_url'), 'user_group': live.get('user_group'),
            'period': live.get('period'), 'window_start': live.get('window_start') or '', 'window_end': live.get('window_end') or '',
            'fetched_at': live.get('fetched_at'), 'cards_matched': len(obs), 'cards_unmatched': len(unmatched),
            'forecast_model': next((c.get('gih_model_version') for c in cards), ''), 'forecast_cards': len(cards)}
    with open(out / 'trk_snapshot.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(snap)); w.writeheader(); w.writerow(snap)
    print(json.dumps({'cards': len(rows), 'matched': len(obs), 'with_gih': sum(r['obs_gih'] is not None for r in rows),
                      'unmatched': unmatched[:30]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
