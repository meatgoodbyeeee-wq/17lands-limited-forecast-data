#!/usr/bin/env python3
"""G1 v2: run the Opus judgements with `claude -p` (PLAN_v2.md 12.2).

  python3 run_v2.py run [--passes p1,p2,p3] [--sets past|fra] [--jobs 4]
      judge every batch of input_v2/<pass>/ whose raw_v2/<pass>/<batch>.txt is missing or fails the check;
      a failing batch is re-run whole, at most 2 extra attempts. Attempts go to raw_v2_log/attempts.csv.
  python3 run_v2.py status    # batches done / missing per pass

No FRA outcome is read here. FRA batches are only judged with --sets fra (after the P1-P4 gate passes).
"""
import argparse, csv, json, re, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = 'claude-opus-5-5'
LINE = re.compile(r'^(\d+)((?: \d+){7})\s*$')
MAX = [4, 4, 4, 4, 3, 4, 10]
PASSES = ['p1', 'p2', 'p3']
MAX_ATTEMPTS = 3  # first try + 2 re-runs
_lock = threading.Lock()


def call_claude(system_file: Path, user_text: str, timeout=1800):
    """One independent CLI call: given system prompt, no tools, no MCP, no settings, empty working dir."""
    with tempfile.TemporaryDirectory(prefix='g1v2_') as d:
        cmd = ['claude', '-p', '--model', MODEL, '--system-prompt-file', str(system_file),
               '--tools', '', '--strict-mcp-config', '--setting-sources', '',
               '--no-session-persistence', '--output-format', 'json']
        r = subprocess.run(cmd, input=user_text, capture_output=True, text=True, cwd=d, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f'claude exit {r.returncode}: {r.stderr[-500:]}')
    j = json.loads(r.stdout)
    if j.get('is_error'):
        raise RuntimeError(f'claude error: {str(j.get("result"))[:500]}')
    return j


def extract(text):
    """Keep only '<id> <7 ints>' lines; return (lines, n_dropped_nonempty)."""
    keep, drop = [], 0
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if LINE.match(s):
            keep.append(s)
        else:
            drop += 1
    return keep, drop


def needed_ids(input_file: Path):
    return {int(x) for x in re.findall(r'^#(\d+) \|', input_file.read_text(), re.M)}


def validate(lines, need):
    got, errs = {}, []
    for s in lines:
        m = LINE.match(s)
        i, v = int(m.group(1)), [int(x) for x in m.group(2).split()]
        if any(x < 0 or x > mx for x, mx in zip(v, MAX)):
            errs.append(f'out of range {s}')
        if i in got:
            errs.append(f'duplicate {i}')
        got[i] = v
    miss, extra = need - set(got), set(got) - need
    if miss:
        errs.append(f'missing {len(miss)}')
    if extra:
        errs.append(f'extra {len(extra)}')
    return errs


def log_attempt(row):
    f = HERE / 'raw_v2_log' / 'attempts.csv'
    with _lock:
        new = not f.exists()
        with f.open('a', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)


def judge_batch(p, batch, system_file=HERE / 'RUBRIC_v2.md', in_dir=None, out_dir=None, log_dir=None):
    in_dir = in_dir or HERE / 'input_v2' / p
    out_dir = out_dir or HERE / 'raw_v2' / p
    log_dir = log_dir or HERE / 'raw_v2_log' / p
    out_dir.mkdir(parents=True, exist_ok=True); log_dir.mkdir(parents=True, exist_ok=True)
    inp = in_dir / f'{batch}.txt'
    need = needed_ids(inp)
    out = out_dir / f'{batch}.txt'
    if out.exists() and not validate(extract(out.read_text())[0], need):
        return 'skip'
    for a in range(1, MAX_ATTEMPTS + 1):
        t0 = time.time(); status, errs, drop, usage = 'ok', [], 0, {}
        try:
            j = call_claude(system_file, inp.read_text())
            (log_dir / f'{batch}.a{a}.json').write_text(json.dumps(j, ensure_ascii=False, indent=1))
            lines, drop = extract(j.get('result', ''))
            errs = validate(lines, need)
            usage = j.get('usage', {})
            if not errs:
                out.write_text('\n'.join(lines) + '\n')
            else:
                status = 'invalid'
        except Exception as ex:  # noqa: BLE001
            status, errs = 'error', [str(ex)[:300]]
        log_attempt({'pass': p, 'batch': batch, 'attempt': a, 'status': status, 'errors': '; '.join(errs)[:300],
                     'dropped_lines': drop, 'n_cards': len(need), 'seconds': round(time.time() - t0),
                     'input_tokens': usage.get('input_tokens', ''), 'output_tokens': usage.get('output_tokens', ''),
                     'time': time.strftime('%Y-%m-%dT%H:%M:%S')})
        print(f'{p}/{batch} attempt {a}: {status} {"; ".join(errs)[:120]}', flush=True)
        if status == 'ok':
            return 'ok'
    return 'failed'


def batches(passes, sets):
    rows = list(csv.DictReader((HERE / 'batches.csv').open()))
    for r in rows:
        if r['pass'] in passes and ((sets == 'fra') == (r['set'] == 'FRA')):
            yield r['pass'], r['batch']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'status'])
    ap.add_argument('--passes', default='p1,p2,p3')
    ap.add_argument('--sets', default='past', choices=['past', 'fra'])
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    passes = a.passes.split(',')
    todo = list(batches(passes, a.sets))
    if a.cmd == 'status':
        for p in passes:
            bs = [b for q, b in todo if q == p]
            done = sum((HERE / 'raw_v2' / p / f'{b}.txt').exists() for b in bs)
            print(f'{p} ({a.sets}): {done}/{len(bs)} batches written')
        return 0
    gate_f = HERE / 'eval_v2' / 'past_gate.json'
    gate = json.loads(gate_f.read_text()) if gate_f.exists() else {}
    if a.sets == 'fra' and not (gate.get('all_pass') is True and gate.get('selftest') is False):
        sys.exit('FRA judging is allowed only after the P1-P4 gate passes (eval_v2/past_gate.json).')
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda pb: judge_batch(*pb), todo))
    print({k: res.count(k) for k in set(res)})
    return 1 if 'failed' in res else 0


if __name__ == '__main__':
    sys.exit(main())
