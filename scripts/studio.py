"""Run the studio safely while working on it.

    python scripts/studio.py test-copy [--port 8831]   # a throwaway studio with its own data
    python scripts/studio.py stop [--port 8831]        # stop that copy
    python scripts/studio.py redeploy                  # restart the dev service and prove it's up

test-copy: starts this checkout on 127.0.0.1:PORT with VEFR_DATA_DIR set to a fresh
temporary folder, so browser tests and experiments never write the real data/
(on 2026-09-27 a test wrote the owner's learning record). Model settings are
passed through from the environment (VEFR_LLAMACPP_URL, VEFR_STORYTELLER, ...).
Prints the URL and the data folder, then returns once /api/health answers.

redeploy: `systemctl --user restart` the dev service (VEFR_SERVICE, default
vefr-dev.service), then waits for /api/health on VEFR_PORT (default 8820) and
prints the commit it is serving. Exits non-zero if it doesn't come back.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(tempfile.gettempdir()) / "vefr-test-copies"


def health(port: int, timeout: float = 30.0) -> dict | None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as r:
                return json.loads(r.read() or b"{}")
        except Exception:  # noqa: BLE001 - not up yet
            time.sleep(0.5)
    return None


def test_copy(port: int) -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix=f"vefr-data-{port}-"))
    env = {**os.environ, "VEFR_DATA_DIR": str(data)}
    log = open(STATE / f"{port}.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "vefr.main:app", "--app-dir", str(ROOT / "src"),
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (STATE / f"{port}.json").write_text(json.dumps({"pid": proc.pid, "data": str(data)}))
    if health(port) is None:
        print(f"the test copy didn't start; see {STATE / f'{port}.log'}", file=sys.stderr)
        stop(port)
        return 1
    print(f"test copy: http://127.0.0.1:{port}/  (data: {data})")
    return 0


def stop(port: int) -> int:
    f = STATE / f"{port}.json"
    if not f.is_file():
        print(f"no test copy on port {port}")
        return 0
    info = json.loads(f.read_text())
    try:
        os.killpg(info["pid"], signal.SIGTERM)
    except ProcessLookupError:
        pass
    f.unlink()
    print(f"stopped the test copy on port {port} (its data stays in {info['data']})")
    return 0


def redeploy() -> int:
    service = os.environ.get("VEFR_SERVICE", "vefr-dev.service")
    port = int(os.environ.get("VEFR_PORT", "8820"))
    r = subprocess.run(["systemctl", "--user", "restart", service], capture_output=True, text=True)
    if r.returncode:
        print(f"couldn't restart {service}: {r.stderr.strip()}", file=sys.stderr)
        return 1
    h = health(port, timeout=60)
    if h is None:
        print(f"{service} restarted but /api/health on :{port} never answered", file=sys.stderr)
        return 1
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    print(f"{service} is up on :{port} at {commit or 'unknown commit'}: {json.dumps(h)[:200]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["test-copy", "stop", "redeploy"])
    ap.add_argument("--port", type=int, default=8831)
    a = ap.parse_args()
    if a.what == "test-copy":
        return test_copy(a.port)
    if a.what == "stop":
        return stop(a.port)
    return redeploy()


if __name__ == "__main__":
    sys.exit(main())
