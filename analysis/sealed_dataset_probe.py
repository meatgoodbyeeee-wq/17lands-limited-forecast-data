#!/usr/bin/env python3
import urllib.request,gzip,csv,io,json
url="https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.TDM.Sealed.csv.gz"
req=urllib.request.Request(url,headers={"User-Agent":"LimitedForecastResearch/4.0"})
raw=urllib.request.urlopen(req,timeout=60).read()
print("BYTES",len(raw))
with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
    txt=io.TextIOWrapper(gz,encoding="utf-8")
    r=csv.reader(txt)
    header=next(r)
    row=next(r)
print("NCOLS",len(header))
print("HEADER",json.dumps(header))
print("ROW",json.dumps(dict(zip(header,row))))
