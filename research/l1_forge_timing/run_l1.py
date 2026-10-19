"""L1 runner: round-robin groups of decks through Forge `sim`, logging instant/flash casts (patched Forge).

usage: python3 -I run_l1.py <FORGE_REPO> <DECK_DIR> <OUT_DIR> <GROUP_SIZE> <SEED> [WORKERS]
Each group of GROUP_SIZE decks plays a RoundRobin with 1 game per pair (-m 1). Per group: <OUT_DIR>/g<k>.log (L1 casts),
g<k>.out (sim output). Tournament mode ignores -a, so both sides use the Default AI profile.
"""
import concurrent.futures
import glob
import os
import shutil
import subprocess
import sys

REPO, DECKS, OUT, GS, SEED = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
WORKERS = int(sys.argv[6]) if len(sys.argv) > 6 else 2
JAR = os.path.join(REPO, "forge-gui-desktop/target/forge-gui-desktop-2.0.16-SNAPSHOT-jar-with-dependencies.jar")
os.makedirs(OUT, exist_ok=True)
decks = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DECKS, "*.dck")))
groups = [decks[i:i + GS] for i in range(0, len(decks) - GS + 1, GS)]


def run(k):
    names = groups[k]
    log, out = os.path.join(OUT, f"g{k}.log"), os.path.join(OUT, f"g{k}.out")
    if os.path.exists(log):
        os.remove(log)
    # tournament mode loads every .dck in the -D folder (and ignores -a), so give each group its own folder
    gdir = os.path.join(OUT, f"decks_g{k}")
    os.makedirs(gdir, exist_ok=True)
    for n in names:
        shutil.copy(os.path.join(DECKS, n), os.path.join(gdir, n))
    cmd = ["java", "-Xmx2g", "-jar", JAR, "sim", "-D", gdir, "-t", "RoundRobin", "-m", "1",
           "-s", str(SEED + k), "-q"]
    env = dict(os.environ, L1_LOG=log)
    with open(out, "w") as fo:
        subprocess.run(cmd, cwd=os.path.join(REPO, "forge-gui"), env=env, stdout=fo, stderr=subprocess.STDOUT, timeout=3000)
    return k


with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
    for k in ex.map(run, range(len(groups))):
        print("group", k, "done", flush=True)
