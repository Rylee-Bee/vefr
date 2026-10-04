"""Acceptance for `scripts/bench_floors.py` (E0a).

Runs the Python floor bench small (5 seeds, one size) and checks:

  - the JSON report's shape (top-level keys, per-size entry);
  - the deterministic counts actually cover every seed
    (stair-distance and reachability sums must add to --seeds);
  - a second run reproduces the same counts exactly - only timings
    may differ between runs.

The bench itself is deliberately not a pytest plugin: it is a script
so `uv run python scripts/bench_floors.py` works standalone.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bench_floors.py"

# The deterministic half of a per-size entry: everything except the
# timings (`gen_ms`), which are expected to vary run to run.
DETERMINISTIC = ("seeds", "stair_distance", "reachability",
                 "walkable_tiles", "stair_to_stair_turns")


def run_bench(tmp_path: Path, name: str) -> dict:
    """Run the bench once, return its parsed JSON report."""
    out = tmp_path / name
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--seeds", "5", "--size", "48x32x16",
         "--json", str(out), "--quiet"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    assert proc.returncode == 0, f"bench failed:\n{proc.stdout}\n{proc.stderr}"
    assert out.is_file(), "bench wrote no --json report"
    return json.loads(out.read_text(encoding="utf-8"))


def test_report_shape(tmp_path):
    report = run_bench(tmp_path, "py.json")

    assert report["bench"] == "vefr-floor-bench"
    assert report["version"] == 1
    assert report["seeds"] == ["bench-0", "bench-1", "bench-2",
                               "bench-3", "bench-4"]
    assert report["sizes"] == [[48, 32, 16]]
    assert report["command"].startswith("uv run python scripts/bench_floors.py")
    assert set(report["results"]) == {"48x32x16"}

    entry = report["results"]["48x32x16"]
    assert entry["seeds"] == 5

    # Counts cover every seed, exactly once each.
    stair = entry["stair_distance"]
    assert stair["min_10_or_more"] + stair["fallback_below_10"] == 5
    reach = entry["reachability"]
    assert reach["all_walkable_reachable"] + reach["disconnected"] == 5

    # Timings present and sane.
    gen = entry["gen_ms"]
    assert gen["max"] >= gen["p95"] >= gen["p50"] >= 0

    walk = entry["walkable_tiles"]
    assert 0 < walk["min"] <= walk["p50"] <= walk["max"]

    path = entry["stair_to_stair_turns"]
    assert path is not None and path["p50"] >= 1


def test_counts_repeat_across_runs(tmp_path):
    """Deterministic counts are identical between runs; only times differ."""
    first = run_bench(tmp_path, "a.json")
    second = run_bench(tmp_path, "b.json")

    entry_a = first["results"]["48x32x16"]
    entry_b = second["results"]["48x32x16"]
    for key in DETERMINISTIC:
        assert entry_a[key] == entry_b[key], f"{key} changed between runs"
