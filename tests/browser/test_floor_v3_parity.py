"""delve v3 parity in Chromium, and the budget PLAN.md section 3 sets.

The normative measurement for slice E3. `tests/test_floor_v3_parity.py` runs
the same cases through the same woven player in jsdom, on node, which is the
path a throwaway clone can run; this file is the browser the game actually
plays in, so this is where the two numbers the plan asks for are taken:

  - **per-stage parity** over 200 seeds x every size x every floor kind, plus
    the stamped half, compared against `vefr.delve_v3` case for case. The same
    canonical JSON, the same comparison helpers and the same seed count as the
    node path (`tests/floor_v3_parity_cases.py`); only the engine under the
    twin differs.
  - **generate + validate, p95 over the 200 seeds**: <= 40 ms desktop and
    <= 150 ms on the phone proxy, which is Chromium at a 4x CPU throttle
    (`Emulation.setCPUThrottlingRate`, the same throttle the E0a bench uses).

Skipped when Playwright's Chromium is not installed, which is the repo's
browser convention; `VEFR_BROWSER_REQUIRED=1` makes that a failure instead
(CI's browser job).

    uv run playwright install chromium      # once
    uv run pytest -q tests/browser/test_floor_v3_parity.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from vefr import cli

# The shared cases module lives one directory up, in `tests/`. Loaded by path
# rather than by name so this file does not depend on how the runner put
# `tests/` on the path for the node-side twin of the same comparison.
_SPEC = importlib.util.spec_from_file_location(
    "floor_v3_parity_cases",
    Path(__file__).resolve().parents[1] / "floor_v3_parity_cases.py")
cases = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cases)

ROOT = cases.ROOT
CANON = ROOT / "tests" / "fixtures" / "floor_plan_canon.mjs"

# One evaluate call per chunk: the record of a 128x96 floor is about 20 KB of
# canonical JSON, so a chunk of 200 is a few MB through the protocol - large
# enough that the call overhead is nothing, small enough that the return is.
CHUNK = 200

VIEWPORT = {"width": 1280, "height": 800}

# The budget of PLAN.md section 3.
BUDGET_DESKTOP_MS = 40.0
BUDGET_PHONE_MS = 150.0

# The canonical form and the per-case draw, injected once into the page. The
# twin itself is already in the page: the woven player IS the page.
SETUP = """
window.__V3 = __PAYLOAD__;
(function () {
__CANON__
  window.__canon = canon;
})();
"""

DRAW_ONE = """
(ks) => ks.map((k) => {
  const D = window.VEFR_DELVE, C = window.__canon, P = window.__V3;
  const pack = P.packs[k.pack];
  const records = k.stamped ? P.stamps : [];
  const key = k.seed + '/' + pack.id + '/' + k.kind;
  const empty = { i: k.i, plan: '', layout: '', graph: '', pop: '', floor: '',
                  failed: '', gen: -1 };
  if (!D || typeof D.v3Attempt !== 'function') return empty;
  let got;
  try {
    got = D.v3Attempt(key, k.w, k.h, pack, k.kind, records, P.depth, false);
  } catch (err) {
    return Object.assign(empty, { failed: 'threw: ' + (err && err.message) });
  }
  let gen = -1;
  try {
    const full = D.generateFloorV3(k.seed, [k.w, k.h], pack, k.kind, records, P.depth);
    gen = full.gen;
    // The whole floor comes back only where the stage comparison could not
    // already have covered it: a v2 fallback, or a floor whose first attempt
    // gave up and the retry ladder then drew.
    if (!(gen === 3 && got.failed === '')) return Object.assign(empty, {
      plan: C(got.plan), layout: C(got.layout),
      graph: got.graph === null ? '' : C(got.graph),
      pop: got.pop === null ? '' : C(got.pop),
      floor: got.floor === null ? '' : C(got.floor),
      failed: got.failed, gen: gen, full: C(full),
    });
  } catch (err) {
    return Object.assign(empty, { failed: 'threw: ' + (err && err.message) });
  }
  return {
    i: k.i,
    plan: C(got.plan),
    layout: C(got.layout),
    graph: got.graph === null ? '' : C(got.graph),
    pop: got.pop === null ? '' : C(got.pop),
    floor: got.floor === null ? '' : C(got.floor),
    failed: got.failed,
    gen: gen,
    full: '',
  };
});
"""

# One timed sample per seed, with the warm-up generation discarded: Chromium's
# `performance.now()` resolves about 0.1 ms, which is fine for a floor and not
# fine for a first call that pays for a JIT.
PERF_ONE = """
([w, h, kind, pack, stamps, depth, seeds]) => {
  const D = window.VEFR_DELVE;
  const times = [];
  for (const seed of seeds) {
    D.generateFloorV3(seed, [w, h], pack, kind, stamps, depth);
    const t0 = performance.now();
    D.generateFloorV3(seed, [w, h], pack, kind, stamps, depth);
    times.push(performance.now() - t0);
  }
  return times;
}
"""


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: sorted[floor(p * (n - 1))]."""
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(p * (len(ordered) - 1)))]


def _canon_source() -> str:
    return CANON.read_text(encoding="utf-8").replace("export function", "function")


@pytest.fixture(scope="module")
def player(browser, tmp_path_factory):
    """The shipped player, woven and open in a real page."""
    home = tmp_path_factory.mktemp("floor-v3-chromium")
    html = home / "player.html"
    html.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    context = browser.new_context(viewport=VIEWPORT)
    page = context.new_page()
    page.goto(html.as_uri())
    assert page.evaluate("() => !!(window.VEFR_DELVE && window.VEFR_DELVE.v3Attempt)"), (
        "the woven player carries no v3 twin: window.VEFR_DELVE.v3Attempt is missing")
    page.evaluate(SETUP.replace("__PAYLOAD__", json.dumps(_v3_payload()))
                  .replace("__CANON__", _canon_source()))
    yield page, context
    context.close()


def _v3_payload() -> dict:
    file = cases.case_file()
    return {"packs": file["packs"], "stamps": file["stamps"], "depth": file["depth"]}


def _all_cases() -> list[dict]:
    return cases.case_file()["cases"]


def test_the_twin_draws_the_same_floor_in_chromium(player):
    """Every case of the sweep, in the browser the game plays in."""
    page, _context = player
    index = cases.by_index()
    stages: list[dict] = []
    full: list[dict] = []
    every = _all_cases()
    for start in range(0, len(every), CHUNK):
        chunk = every[start:start + CHUNK]
        for record in page.evaluate(DRAW_ONE, chunk):
            got = dict(record)
            if got["gen"] == -1:
                # The twin is missing or threw before it drew anything: the
                # stage comparison reports it as a stage mismatch with the
                # reason, rather than the run dying here.
                got["failed"] = got["failed"] or "the twin drew nothing"
            stages.append({k: got[k] for k in ("i", "plan", "layout", "graph",
                                               "pop", "floor", "failed")})
            full.append({"i": got["i"], "gen": got["gen"], "floor": got.get("full", "")})

    expected = len(every)
    reached = cases.reached()
    assert len(stages) == expected, f"drew {len(stages)} of {expected} cases"
    stage_report = cases.compare_stages(stages, index)
    assert stage_report["cases"] == expected, (
        f"the browser replayed {stage_report['cases']} of {expected} cases")
    for stage in cases.STAGES:
        assert stage_report["compared"][stage] == reached[stage], (
            f"{stage_report['compared'][stage]} cases reached the {stage} stage "
            f"in Chromium and the spec takes {reached[stage]} there")
    assert not stage_report["mismatches"], (
        f"{len(stage_report['mismatches'])} stage mismatches in Chromium "
        f"(first {cases.REPORTED} shown):\n"
        + cases.as_lines(stage_report["mismatches"]))

    full_report = cases.compare_full(full, index)
    assert full_report["compared"] == expected, (
        f"the browser replayed {full_report['compared']} of {expected} floors "
        "end to end")
    problems = full_report["gen_mismatches"] + full_report["floor_mismatches"]
    assert not problems, (
        f"{len(problems)} end-to-end mismatches in Chromium:\n"
        + cases.as_lines(problems))
    print(f"\nv3 parity in Chromium: {expected} floors over "
          f"{cases.SEED_COUNT} seeds x {len(cases.SIZES) + len(cases.STAMP_SIZES)} "
          f"sizes x {len(cases.FLOOR_KINDS)} kinds, "
          f"{full_report['fallbacks']} v2 fallbacks")


def test_generation_stays_inside_the_budget_in_chromium(player):
    """PLAN.md section 3: <= 40 ms desktop, <= 150 ms on the phone proxy.

    200 seeds at every size, timed in the page, at the desktop CPU rate and at
    `Emulation.setCPUThrottlingRate(4)` - the same throttle the E0a floor bench
    calls the phone proxy.
    """
    page, context = player
    client = context.new_cdp_session(page)
    payload = _v3_payload()
    seeds = list(cases.SEEDS)
    kind = "normal"
    reported = []
    for width, height, _rooms in cases.SIZES:
        pack = payload["packs"][cases.pack_key(kind, width, False)]
        client.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        desk = page.evaluate(PERF_ONE, [width, height, kind, pack, [], payload["depth"], seeds])
        client.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        slow = page.evaluate(PERF_ONE, [width, height, kind, pack, [], payload["depth"], seeds])
        client.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        assert len(desk) == len(slow) == len(seeds), (
            f"{width}x{height}: {len(desk)} desktop and {len(slow)} throttled "
            f"samples, {len(seeds)} expected")
        reported.append((f"{width}x{height}", percentile(desk, 0.50),
                         percentile(desk, 0.95), percentile(slow, 0.95)))
    for label, p50, p95, slow95 in reported:
        print(f"\nv3 {label}: desktop p50 {p50:.2f} ms, p95 {p95:.2f} ms; "
              f"phone proxy (4x) p95 {slow95:.2f} ms")
    for label, _p50, p95, _slow95 in reported:
        assert p95 <= BUDGET_DESKTOP_MS, (
            f"{label}: generate + validate p95 is {p95:.2f} ms over "
            f"{len(seeds)} seeds, and the desktop budget is {BUDGET_DESKTOP_MS:.0f} ms")
    for label, _p50, _p95, slow95 in reported:
        assert slow95 <= BUDGET_PHONE_MS, (
            f"{label}: generate + validate p95 on the phone proxy is "
            f"{slow95:.2f} ms over {len(seeds)} seeds, and the budget is "
            f"{BUDGET_PHONE_MS:.0f} ms")


@pytest.mark.parametrize("size", cases.STAMP_SIZES,
                         ids=[f"{w}x{h}" for w, h, _ in cases.STAMP_SIZES])
def test_a_stamped_floor_draws_the_same_in_chromium(player, size):
    """The stamped half, on its own, so E5b's JS half has its own failure.

    A stamped floor is where the twin has the most to get wrong - an
    orientation, a socket, a corridor routed round a locked tile - so the
    stamped cases are replayed in Chromium as their own test and the failure
    names the stamp placement rather than the whole sweep.
    """
    page, _context = player
    width, height, _rooms = size
    index = cases.by_index()
    chunk = [case for case in _all_cases()
             if case["stamped"] and case["w"] == width]
    assert chunk, f"no stamped cases at {width}x{height}"
    stages: list[dict] = []
    for start in range(0, len(chunk), CHUNK):
        for record in page.evaluate(DRAW_ONE, chunk[start:start + CHUNK]):
            stages.append({k: record[k] for k in ("i", "plan", "layout", "graph",
                                                  "pop", "floor", "failed")})
    report = cases.compare_stages(stages, index)
    assert len(stages) == len(chunk), (
        f"Chromium drew {len(stages)} of {len(chunk)} stamped floors at {width}x{height}")
    assert not report["mismatches"], (
        f"{len(report['mismatches'])} stamped mismatches in Chromium at "
        f"{width}x{height} (first {cases.REPORTED} shown):\n"
        + cases.as_lines(report["mismatches"]))