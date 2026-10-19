"""K2 runner: resumable. Runs K1's 40-deck round-robin jobs in Forge for one or more (arm, job) pairs in parallel.

usage: python3 -I run_k2.py <FORGE_REPO> <DECK_ROOT> <OUT_DIR> <WORKERS> <arm:job> [<arm:job> ...]
  arm = base (no patches) or patch (L3_PATCH=1 L4S_PATCH=1 L5A_PATCH=1)
For each pair: skips if <OUT_DIR>/<arm>/job<j>.json already exists. Otherwise runs
  sim -D <DECK_ROOT>/job<j> -t RoundRobin -m 1 -s <1000+j> -q   with env L1_LOG=<OUT_DIR>/<arm>/job<j>.log
and, when the run ends with all games finished, converts the log into job<j>.json in K1's format
([{"winner": deck or null, "draws": {deck: [cards]}}]) and gzips the log. A per-job time limit keeps each
background chunk under the session's 2-hour cap; an unfinished job leaves no .json and is simply re-run.
"""
import concurrent.futures
import gzip
import json
import os
import shutil
import subprocess
import sys
import time

REPO, DECKS, OUT, WORKERS = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
PAIRS = [p.split(":") for p in sys.argv[5:]]
JAR = os.path.join(REPO, "forge-gui-desktop/target/forge-gui-desktop-2.0.16-SNAPSHOT-jar-with-dependencies.jar")
ARM_ENV = {"base": {}, "patch": {"L3_PATCH": "1", "L4S_PATCH": "1", "L5A_PATCH": "1"}}
JOB_LIMIT_S = 105 * 60


def convert(log_path):
    games, cur = [], None
    for line in open(log_path, encoding="utf-8"):
        f = line.rstrip("\n").split("|")
        if f[0] == "START":
            cur = {"winner": None, "draws": {}}
            games.append(cur)
        elif cur is None:
            continue
        elif f[0] == "DRAW":
            cur["draws"].setdefault(f[2], [])
            if f[1] not in cur["draws"][f[2]]:
                cur["draws"][f[2]].append(f[1])
        elif f[0] == "END":
            cur["winner"] = None if f[1] in ("null", "None") else f[1]
    return games


def run(arm, j):
    od = os.path.join(OUT, arm)
    os.makedirs(od, exist_ok=True)
    js, log, out = (os.path.join(od, f"job{j}.{x}") for x in ("json", "log", "out"))
    if os.path.exists(js):
        return f"{arm} job{j}: already done"
    if os.path.exists(log):
        os.remove(log)
    ndecks = len([f for f in os.listdir(os.path.join(DECKS, f"job{j}")) if f.endswith(".dck")])
    expected = ndecks * (ndecks - 1) // 2
    env = dict(os.environ, L1_LOG=log, **ARM_ENV[arm])
    t0 = time.time()
    cmd = ["java", "-Xmx2g", "-jar", JAR, "sim", "-D", os.path.join(DECKS, f"job{j}"), "-t", "RoundRobin", "-m", "1",
           "-s", str(1000 + int(j)), "-q"]
    try:
        with open(out, "w") as fo:
            subprocess.run(cmd, cwd=os.path.join(REPO, "forge-gui"), env=env, stdout=fo, stderr=subprocess.STDOUT,
                           timeout=JOB_LIMIT_S)
    except subprocess.TimeoutExpired:
        return f"{arm} job{j}: TIME LIMIT after {time.time() - t0:.0f}s (will be re-run)"
    games = convert(log)
    ended = sum(1 for g in games if "draws" in g and (g["winner"] is not None or g["draws"]))
    if len(games) < expected:
        return f"{arm} job{j}: incomplete {len(games)}/{expected} games (will be re-run)"
    json.dump(games, open(js + ".tmp", "w"))
    os.replace(js + ".tmp", js)
    with open(log, "rb") as fi, gzip.open(log + ".gz", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    os.remove(log)
    return f"{arm} job{j}: done {len(games)} games ({ended} with draws) in {time.time() - t0:.0f}s"


with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
    for msg in ex.map(lambda p: run(*p), PAIRS):
        print(time.strftime("%H:%M:%S"), msg, flush=True)
