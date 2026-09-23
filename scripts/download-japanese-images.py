"""Mirror verified official Japanese images using the checked-in URL/hash manifest."""
import concurrent.futures
import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'assets/fra/ja/manifest.json').read_text())

def download(entry):
    url = urllib.parse.urlsplit(entry['url'])
    if url.scheme != 'https' or url.hostname != 'media.wizards.com':
        raise ValueError('Expected official Wizards HTTPS image')
    path = ROOT / 'assets/fra/ja' / entry['filename']
    if path.parent != ROOT / 'assets/fra/ja':
        raise ValueError('Invalid filename')
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']:
        return
    req = urllib.request.Request(entry['url'], headers={'User-Agent': 'LimitedForecast/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('Official image changed: ' + entry['filename'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    list(pool.map(download, manifest['files']))
print(f"Verified {len(manifest['files'])} official Japanese image files")
