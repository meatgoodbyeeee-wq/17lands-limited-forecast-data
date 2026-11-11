#!/usr/bin/env python3
"""TRK observed values from 17Lands Card Data (GitHub Actions only; the sandbox cannot reach 17Lands).

Rules (user decision 2026-11-11):
- All users only. Never sends user_group (the top-player TRK values stay unseen until top forecasts are frozen).
- At most one card-data attempt per JST calendar day; the state file records every attempt, so a rerun on the same day does
  nothing. If the filters list shows no TRK, no card-data request is made and the day stays open (fix the code, push again).
- At most 3 HTTP requests per attempt: the filters list (to confirm the 17Lands set code), the card data for the window,
  and, only if the window query returns no games at all, the same card data with time_period=ALL_TIME.
- The result is for private comparison only. Nothing here touches forecasts.

Output: live/trk-card-data.json (only on success with games), live/trk-card-data-state.json (every attempt).
FAKE_17LANDS=<dir> reads filters.json and card_data.json from a directory instead of the network (local tests).
NOW=<ISO time> overrides the clock.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT, STATE = ROOT / 'live/trk-card-data.json', ROOT / 'live/trk-card-data-state.json'
CODE, ARENA_RELEASE = os.environ.get('TRK_17LANDS_CODE', 'TRK'), '2026-11-10'
UA = 'Sakiyomi/1.0 (limited forecast research; once a day)'
KEEP = ('name', 'color', 'rarity', 'seen_count', 'avg_seen', 'pick_count', 'avg_pick', 'game_count', 'win_rate',
        'opening_hand_game_count', 'opening_hand_win_rate', 'drawn_game_count', 'drawn_win_rate',
        'ever_drawn_game_count', 'ever_drawn_win_rate', 'never_drawn_game_count', 'never_drawn_win_rate',
        'drawn_improvement_win_rate', 'pool_count', 'play_rate')


def now():
    return datetime.fromisoformat(os.environ['NOW'].replace('Z', '+00:00')) if os.environ.get('NOW') else datetime.now(timezone.utc)


def get(url, fake_name):
    fake = os.environ.get('FAKE_17LANDS')
    if fake:
        return json.loads((Path(fake) / fake_name).read_text())
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    t = now()
    jst = (t + timedelta(hours=9)).date().isoformat()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if state.get('last_attempt_date_jst') == jst and state.get('card_data_called'):
        print(f'no request: already attempted on {jst} (JST)')
        return 0
    state = {'last_attempt_date_jst': jst, 'last_attempt_at': t.isoformat(timespec='seconds'), 'requests': [], 'card_data_called': False}
    try:
        code = CODE
        try:
            f = get('https://www.17lands.com/data/filters', 'filters.json')
            exps = f.get('expansions') or []
            state['filters_has_trk'] = CODE in exps
            state['filters_expansions'] = exps[:80]
            if exps and CODE not in exps:
                state['result'] = f'{CODE} not in the 17Lands filters list; no card-data request made'
                state['requests'].append('filters')
                print(state['result'])
                return 0
            start = (f.get('start_dates') or {}).get(CODE) or ARENA_RELEASE
            state['requests'].append('filters')
        except Exception as e:  # the filters list is only a check; continue with the known code
            state['filters_error'] = repr(e)[:300]
            start = ARENA_RELEASE
        start = str(start)[:10]
        end = t.date().isoformat()  # 17Lands dates are UTC; today's partial day is included
        q = {'expansion': code, 'event_type': 'PremierDraft', 'start_date': start, 'end_date': end}
        url = 'https://www.17lands.com/api/card_data?' + urllib.parse.urlencode(q)
        state['card_data_called'] = True
        rows = get(url, 'card_data.json'); state['requests'].append('card_data_window')
        games = sum(int(r.get('game_count') or 0) for r in rows) if isinstance(rows, list) else 0
        period = 'window'
        if games == 0:
            url = 'https://www.17lands.com/api/card_data?' + urllib.parse.urlencode({'expansion': code, 'event_type': 'PremierDraft', 'time_period': 'ALL_TIME'})
            rows = get(url, 'card_data.json'); state['requests'].append('card_data_all_time')
            games = sum(int(r.get('game_count') or 0) for r in rows) if isinstance(rows, list) else 0
            period = 'all_time'
        state.update(rows=len(rows) if isinstance(rows, list) else None, games_sum=games, url=url)
        if not isinstance(rows, list) or games == 0:
            state['result'] = 'no games yet; snapshot not written'
            print(state['result'])
            return 0
        cards = [{k: r.get(k) for k in KEEP if k in r} for r in rows]
        doc = {'schema': 1, 'source': '17Lands', 'source_type': 'Card Data', 'attribution': '17Lands (17lands.com) Card Data',
               'expansion': code, 'format': 'PremierDraft', 'user_group': 'all', 'period': period,
               'window_start': start if period == 'window' else None, 'window_end': end if period == 'window' else None,
               'source_url': url, 'fetched_at': t.isoformat(timespec='seconds'), 'fetched_date_jst': jst,
               'cards_with_games': sum(1 for r in rows if (r.get('ever_drawn_game_count') or 0) > 0), 'cards': cards}
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=0) + '\n')
        state['result'] = f'saved {len(cards)} rows ({period} {start}..{end})'
        print(state['result'])
        return 0
    except Exception as e:
        state['result'] = 'error: ' + repr(e)[:300]
        print(state['result'], file=sys.stderr)
        return 0  # the state must still be saved so the same JST day is not retried
    finally:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + '\n')


if __name__ == '__main__':
    sys.exit(main())
