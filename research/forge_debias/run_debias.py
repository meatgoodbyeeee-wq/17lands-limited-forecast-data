"""forge-debias の実行(K3 の run_k2.py の base 条件と同じ。記録だけ増やす)。再開できる。

usage: python3 -I run_debias.py <FORGE_REPO> <DECK_ROOT> <OUT_DIR> <WORKERS> <job> [<job> ...]
各ジョブ: <OUT_DIR>/job<j>.json があれば飛ばす。なければ
  java -jar forge sim -D <DECK_ROOT>/job<j> -t RoundRobin -m 1 -s <1000+j> -q
を環境変数 L1_LOG=<OUT_DIR>/job<j>.log FORGE_SIM_SEEN=1 で実行する(挙動を変える環境変数は渡さない)。
全試合が終わったら job<j>.json に変換する:
  [{"winner": デッキ名 or null, "draws": {デッキ: [引いたカード]}, "hand_end": {デッキ: [終了時に手札にあったカード]},
    "turns": 終了ターン, "timeouts": AI の判断の打ち切り回数}]
ログ(.log と .out)は gzip して残す。1 ジョブの上限は JOB_LIMIT_S 秒で、超えたら残骸を消して再実行の対象にする。
"""
import concurrent.futures
import gzip
import json
import os
import shutil
import subprocess
import sys
import time

REPO, DECKS, OUT, WORKERS = (os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]),
                              int(sys.argv[4]))
JOBS = sys.argv[5:]
JAR = os.path.join(REPO, "forge-gui-desktop/target/forge-gui-desktop-2.0.16-SNAPSHOT-jar-with-dependencies.jar")
JOB_LIMIT_S = int(os.environ.get("JOB_LIMIT_S", str(113 * 60)))


def convert(log_path, out_path):
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
    # .out の Seen 行(1 試合に 2 行、試合の順)と Timeouts 行(1 試合に 1 行)
    seen, touts = [], []
    for line in open(out_path, encoding="utf-8", errors="replace"):
        if line.startswith("Seen: "):
            parts = line.rstrip("\n").split("\t")
            seen.append((parts[1], int(parts[3]), [x for x in parts[4].split("|") if x]))
        elif line.startswith("Timeouts: "):
            touts.append(int(line.rstrip("\n").split("\t")[1]))
    if len(seen) != 2 * len(games) or len(touts) != len(games):
        raise RuntimeError(f"seen {len(seen)} / timeouts {len(touts)} lines for {len(games)} games")
    for i, g in enumerate(games):
        g["hand_end"] = {}
        for deck, turn, cards in seen[2 * i: 2 * i + 2]:
            g["hand_end"][deck] = sorted({c.rsplit("@", 1)[0] for c in cards if c.endswith("@Hand")})
            g["turns"] = turn
        g["timeouts"] = touts[i]
        if set(g["hand_end"]) != set(g["draws"]) and g["draws"]:
            raise RuntimeError(f"game {i}: deck names differ between log and out")
    return games


def gz(path):
    with open(path, "rb") as fi, gzip.open(path + ".gz", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    os.remove(path)


def run(j):
    os.makedirs(OUT, exist_ok=True)
    js, log, out = (os.path.join(OUT, f"job{j}.{x}") for x in ("json", "log", "out"))
    if os.path.exists(js):
        return f"job{j}: already done"
    for p in (log, out):
        if os.path.exists(p):
            os.remove(p)
    ndecks = len([f for f in os.listdir(os.path.join(DECKS, f"job{j}")) if f.endswith(".dck")])
    expected = ndecks * (ndecks - 1) // 2
    env = dict(os.environ, L1_LOG=log, FORGE_SIM_SEEN="1")
    for k in ("L2_PATCH", "L3_PATCH", "L4_PATCH", "L4S_PATCH", "L5A_PATCH", "L5B_PATCH", "S2_PATCH", "L4_LOG", "L1_ALL_SPELLS"):
        env.pop(k, None)
    t0 = time.time()
    cmd = ["java", "-Xmx2g", "-jar", JAR, "sim", "-D", os.path.join(DECKS, f"job{j}"), "-t", "RoundRobin", "-m", "1",
           "-s", str(1000 + int(j)), "-q"]
    try:
        with open(out, "w") as fo:
            subprocess.run(cmd, cwd=os.path.join(REPO, "forge-gui"), env=env, stdout=fo, stderr=subprocess.STDOUT,
                           timeout=JOB_LIMIT_S)
    except subprocess.TimeoutExpired:
        return f"job{j}: TIME LIMIT after {time.time() - t0:.0f}s (will be re-run)"
    try:
        games = convert(log, out)
    except Exception as ex:  # noqa: BLE001
        return f"job{j}: convert failed: {ex} (will be re-run)"
    if len(games) < expected:
        return f"job{j}: incomplete {len(games)}/{expected} games (will be re-run)"
    json.dump(games, open(js + ".tmp", "w"))
    os.replace(js + ".tmp", js)
    gz(log)
    gz(out)
    nt = sum(g["timeouts"] for g in games)
    nw = sum(g["winner"] is None for g in games)
    return f"job{j}: done {len(games)} games in {time.time() - t0:.0f}s (no winner {nw}, AI timeouts {nt})"


with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
    for msg in ex.map(run, JOBS):
        print(time.strftime("%H:%M:%S"), msg, flush=True)
