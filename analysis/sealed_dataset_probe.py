#!/usr/bin/env python3
import urllib.request, urllib.error, json
SETS=["KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"]
patterns=[
 "https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{s}.Sealed.csv.gz",
 "https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{s}.Sealed.tar.gz",
]
out={}
for s in SETS:
    rows=[]
    for pat in patterns:
        url=pat.format(s=s)
        req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"LimitedForecastResearch/4.0"})
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                rows.append({"url":url,"status":r.status,"bytes":int(r.headers.get("Content-Length") or 0),"type":r.headers.get("Content-Type")})
        except urllib.error.HTTPError as e:
            rows.append({"url":url,"status":e.code})
        except Exception as e:
            rows.append({"url":url,"error":str(e)})
    out[s]=rows
print("PROBE",json.dumps(out))
