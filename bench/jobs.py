"""Long jobs (training, benchmarks) with a full log, a status file, and a GPU lock.

    python -m bench.jobs run NAME [--gpu] [--timeout 4h] -- CMD ARGS...
    python -m bench.jobs ls                 # every job: state, age, last log line
    python -m bench.jobs tail NAME [-n 20]  # the end of a job's full log

Why (2026-09-26/27 overnight): training crashed twice out of memory because the
tiny painter and a student shared the card, and runners piped output through
`grep | tail`, so a run that went nan at step 0 looked fine until it finished.

--gpu takes an exclusive lock on the card (flock, so a crashed job can't leave it
held). A job that must wait says who holds it. Every job writes
  $VEFR_JOBS_DIR/NAME/log          everything the command printed
  $VEFR_JOBS_DIR/NAME/status.json  state, command, times, exit code, last line
VEFR_JOBS_DIR defaults to ~/.cache/vefr-jobs.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


def jobs_dir() -> Path:
    return Path(os.environ.get("VEFR_JOBS_DIR", Path.home() / ".cache" / "vefr-jobs"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_status(d: Path, **fields) -> dict:
    path = d / "status.json"
    try:
        st = json.loads(path.read_text())
    except (OSError, ValueError):
        st = {}
    st.update(fields)
    tmp = path.with_name(".status.json.tmp")
    tmp.write_text(json.dumps(st, indent=1))
    os.replace(tmp, path)
    return st


def _last_line(log: Path) -> str:
    try:
        with open(log, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4096))
            lines = [ln for ln in f.read().decode("utf-8", "replace").splitlines() if ln.strip()]
        return lines[-1][:200] if lines else ""
    except OSError:
        return ""


def _seconds(text: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([smh]?)", text.strip())
    if not m:
        raise SystemExit(f"bad timeout {text!r}: use 90s, 30m or 4h")
    return float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


class GpuLock:
    """An exclusive flock on $VEFR_JOBS_DIR/gpu.lock; the file says who holds it."""

    def __init__(self, name: str):
        self.name = name
        self.path = jobs_dir() / "gpu.lock"
        self.fd = None

    def holder(self) -> str:
        try:
            return self.path.read_text().strip() or "another job"
        except OSError:
            return "another job"

    def acquire(self, on_wait=None, poll: float = 5.0) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        told = False
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if on_wait and not told:
                    on_wait(self.holder())
                    told = True
                time.sleep(poll)
        os.ftruncate(self.fd, 0)
        os.write(self.fd, f"{self.name} (pid {os.getpid()}, since {_now()})".encode())

    def release(self) -> None:
        if self.fd is not None:
            os.ftruncate(self.fd, 0)
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


def run(name: str, cmd: list[str], gpu: bool = False, timeout: float | None = None) -> int:
    if not NAME.match(name):
        raise SystemExit(f"bad job name {name!r}")
    if not cmd:
        raise SystemExit("nothing to run: put the command after --")
    d = jobs_dir() / name
    d.mkdir(parents=True, exist_ok=True)
    log = d / "log"
    _write_status(d, name=name, cmd=cmd, gpu=gpu, state="queued", queued_at=_now(),
                  started_at=None, ended_at=None, exit=None, last_line="", pid=os.getpid())
    lock = GpuLock(name) if gpu else None
    if lock:
        lock.acquire(on_wait=lambda who: _write_status(d, state="waiting", waiting_for=who))
    code = 1
    try:
        _write_status(d, state="running", started_at=_now(), waiting_for=None)
        with open(log, "ab") as out:
            out.write(f"== {_now()} {' '.join(cmd)}\n".encode())
            out.flush()
            proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                code = 124
                out.write(f"== timed out after {timeout:.0f}s\n".encode())
    finally:
        state = "done" if code == 0 else ("timed-out" if code == 124 else "failed")
        _write_status(d, state=state, exit=code, ended_at=_now(), last_line=_last_line(log))
        if lock:
            lock.release()
    return code


def listing() -> list[dict]:
    rows = []
    root = jobs_dir()
    if not root.is_dir():
        return rows
    for d in sorted(root.iterdir()):
        try:
            st = json.loads((d / "status.json").read_text())
        except (OSError, ValueError):
            continue
        if st.get("state") in ("running", "waiting", "queued"):
            try:
                os.kill(int(st.get("pid", 0)), 0)
            except (OSError, ValueError):
                st["state"] = "lost"  # the runner died without writing an end
            st["last_line"] = _last_line(d / "log")
        rows.append(st)
    return rows


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(prog="bench.jobs")
    sub = ap.add_subparsers(dest="what", required=True)
    r = sub.add_parser("run")
    r.add_argument("name")
    r.add_argument("--gpu", action="store_true")
    r.add_argument("--timeout")
    sub.add_parser("ls")
    t = sub.add_parser("tail")
    t.add_argument("name")
    t.add_argument("-n", type=int, default=20)
    a = ap.parse_args(argv)
    if a.what == "run":
        return run(a.name, cmd, gpu=a.gpu, timeout=_seconds(a.timeout) if a.timeout else None)
    if a.what == "ls":
        rows = listing()
        if not rows:
            print("no jobs yet")
        for st in rows:
            flag = " [gpu]" if st.get("gpu") else ""
            wait = f" (waiting for {st['waiting_for']})" if st.get("state") == "waiting" else ""
            print(f"{st.get('name')}{flag}: {st.get('state')}{wait}  exit={st.get('exit')}  "
                  f"started={st.get('started_at')}  {st.get('last_line', '')[:90]}")
        return 0
    log = jobs_dir() / a.name / "log"
    if not log.is_file():
        raise SystemExit(f"no job called {a.name!r}")
    print("\n".join(log.read_text(errors="replace").splitlines()[-a.n:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
