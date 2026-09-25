#!/usr/bin/env python3
import urllib.request, urllib.error, json
SETS=["TMT","SOS","MSH","HOB"]
out={}
for s in SETS:
    url=f"https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{s}.Sealed.csv.gz"
    req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"LimitedForecastResearch/5.0"})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            out[s]={"status":r.status,"bytes":int(r.headers.get("Content-Length") or 0),"url":url}
    except urllib.error.HTTPError as e:
        out[s]={"status":e.code,"url":url}
print("SUMMARY",json.dumps(out))
