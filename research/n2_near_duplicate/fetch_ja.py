"""Fetch Japanese printed name/text from Scryfall for the review cards (GitHub Actions only; the sandbox cannot reach Scryfall).
python3 fetch_ja.py review_cards.json review_cards_ja.json"""
import json, sys, time, urllib.parse, urllib.request
src, dst = sys.argv[1], sys.argv[2]
out = {}
def get(q):
    url = 'https://api.scryfall.com/cards/search?' + urllib.parse.urlencode({'q': q, 'unique': 'prints', 'include_multilingual': 'true'})
    req = urllib.request.Request(url, headers={'User-Agent': 'sakiyomi-research/1.0', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.load(r).get('data', [])
    except Exception as e:
        return []
def faces_text(c, key):
    if c.get(key): return c[key]
    return '\n//\n'.join(f.get(key, '') or '' for f in c.get('card_faces', []))
for c in json.load(open(src)):
    k = f"{c['set']}|{c['name']}"
    hits = get(f'!"{c["name"]}" lang:ja')
    time.sleep(0.12)
    same = [h for h in hits if h.get('set', '').upper() == c['set']] or hits
    h = same[0] if same else None
    out[k] = None if not h else {'name': h.get('printed_name') or faces_text(h, 'printed_name'), 'text': faces_text(h, 'printed_text'), 'type': h.get('printed_type_line') or faces_text(h, 'printed_type_line'), 'from_set': h.get('set', '').upper()}
json.dump(out, open(dst, 'w'), ensure_ascii=False, indent=1)
print(sum(v is not None for v in out.values()), '/', len(out))
