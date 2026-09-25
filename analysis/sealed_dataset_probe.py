#!/usr/bin/env python3
import re, urllib.request, urllib.parse, json
from html.parser import HTMLParser

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.text=[]; self._href=None; self._buf=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self._href=dict(attrs).get("href"); self._buf=[]
    def handle_data(self,data):
        if self._href is not None:self._buf.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self._href is not None:
            self.links.append(("".join(self._buf).strip(),self._href))
            self._href=None;self._buf=[]

url="https://www.17lands.com/public_datasets"
req=urllib.request.Request(url,headers={"User-Agent":"LimitedForecastResearch/4.0"})
html=urllib.request.urlopen(req,timeout=60).read().decode("utf-8","replace")
print("HTML_LEN",len(html))
# Print any href containing Sealed or game_data_public or S3.
for m in re.findall(r'href=["\']([^"\']+)["\']',html):
    if any(x.lower() in m.lower() for x in ["sealed","game_data","17lands-public","s3"]):
        print("HREF",m)
# Also dump snippets around HOB/TDM/DFT sealed rows for structure.
for key in ["HOB","TDM","DFT","FDN","BLB","OTJ","MKM","LCI","MOM","LTR","KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","WOE"]:
    i=html.find(">"+key+"<")
    if i>=0:
        sn=html[max(0,i-500):i+1800]
        if "Sealed" in sn:
            print("SNIP",key,re.sub(r"\s+"," ",sn)[:2200])
