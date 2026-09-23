"""Daily FRA Game Data check. No Card Data or Draft Data requests."""
import csv
import datetime as dt
import gzip
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

URL = 'https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.FRA.PremierDraft.csv.gz'
START, END = '2026-09-29', '2026-10-27'
OUTPUT = Path('live/fra-public-game.json')

def aggregate(stream):
    reader = csv.reader(stream)
    header = next(reader)
    event, date, won = [header.index(k) for k in ('event_type', 'game_time', 'won')]
    indices = [(i, header.index('drawn_' + h[13:]), h[13:]) for i, h in enumerate(header) if h.startswith('opening_hand_')]
    if not indices:
        raise ValueError('Missing opening-hand columns')
    out, rows = {}, 0
    for row in reader:
        if len(row) != len(header) or row[event] != 'PremierDraft':
            raise ValueError('Invalid columns or non-PremierDraft row')
        if not START <= row[date] < END:
            continue
        if row[won].lower() not in ('true', 'false'):
            raise ValueError('Invalid game outcome')
        win = row[won].lower() == 'true'
        rows += 1
        for opening, drawn, name in indices:
            a, b = int(row[opening]), int(row[drawn])
            if a < 0 or b < 0:
                raise ValueError('Negative count')
            n = a + b
            if n:
                card = out.setdefault(name, {'name': name, 'gih_n': 0, 'gih_wins': 0})
                card['gih_n'] += n
                card['gih_wins'] += n if win else 0
    if not rows or not out:
        raise ValueError('No valid FRA games in the target window')
    for card in out.values():
        card['gih'] = 100 * card['gih_wins'] / card['gih_n']
    return list(out.values()), rows

def check(previous, now, opener=urllib.request.urlopen):
    stamp = now.isoformat().replace('+00:00', 'Z')
    # The date only starts polling. It never switches the forecast phase.
    if now.date().isoformat() < START:
        return {'checked_at': None, 'status': 'awaiting_release', 'observations': previous.get('observations')}
    if str(previous.get('checked_at', ''))[:10] == stamp[:10]:
        return previous
    result = {**previous, 'checked_at': stamp, 'status': 'unavailable', 'error': None}
    try:
        req = urllib.request.Request(URL, method='HEAD', headers={'User-Agent': 'LimitedForecast/1.0'})
        with opener(req, timeout=60) as response:
            etag = response.headers.get('ETag') or response.headers.get('Last-Modified')
            modified = response.headers.get('Last-Modified')
        old = previous.get('observations')
        if old and etag and old['sources']['game'].get('etag') == etag:
            return {**result, 'status': 'available'}
        req = urllib.request.Request(URL, headers={'User-Agent': 'LimitedForecast/1.0'})
        with opener(req, timeout=120) as response:
            with gzip.GzipFile(fileobj=response) as compressed:
                cards, rows = aggregate(io.TextIOWrapper(compressed, encoding='utf-8-sig', newline=''))
        if old:
            counts = {c['name']: c['gih_n'] for c in cards}
            if any(counts.get(c['name'], 0) < c['gih_n'] for c in old['cards']):
                raise ValueError('Observation counts decreased; retaining previous data')
        result.update(status='available', observations={
            'set': 'FRA', 'format': 'PremierDraft', 'queue': 'BO1',
            'source_kind': '17lands-public-datasets', 'window_start': START,
            'window_end_exclusive': END, 'as_of': stamp,
            'sources': {'game': {'url': URL, 'etag': etag, 'source_timestamp': modified or stamp, 'rows': rows}},
            'cards': cards,
        })
    except urllib.error.HTTPError as e:
        result.update(status='unavailable' if e.code in (403, 404) else 'error', http_status=e.code)
    except Exception as e:
        result.update(status='error', error=type(e).__name__ + ': ' + str(e))
    return result

if __name__ == '__main__':
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {}
    result = check(previous, dt.datetime.now(dt.timezone.utc))
    result.update(schema_version=1, dataset_url=URL, schedule='23 17 * * *', run_url=os.environ.get('FRA_RUN_URL'))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
    temporary.replace(OUTPUT)
    print(json.dumps({'status': result['status'], 'checked_at': result['checked_at'], 'cards': len((result.get('observations') or {}).get('cards', []))}))
