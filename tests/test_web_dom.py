"""Actually executes the web UI's JS against a stubbed DOM.

`node --check` only catches syntax errors. The bug that caused the
real "stuck in house" production incident was an undeclared variable
that only failed at runtime - no syntax checker sees that class of
bug. This test runs state.js, town.js, and index.html's inline
script for real, in a node vm context, and drives the actual user
flows (tab switching, phase sync, forge+keep, movement, the stefna,
the journal tab, the wiki, the trace, the export button).

The harness's fetch stub validates every URL against FastAPI's real
route table, written to a temp JSON file and passed in via
VEFR_ROUTES_JSON - so a renamed route fails here with the real
message instead of passing while live play 404s. See
docs/guides/one-source-of-routes.md.

Skips gracefully if node isn't installed - this must never break the
"uv sync --group test" zero-setup promise in GETTING_STARTED.md for
someone without node. When node is present (it is on the author's
dev boxes), this is real coverage the schema-only tests can't give.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "dom_harness.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def _routes_json() -> str:
    """FastAPI's own route table - the only list of routes there is."""
    from vefr.main import app

    paths = sorted(
        route.path
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/")
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(paths, f)
        return f.name


def test_web_ui_survives_a_full_stubbed_dom_run():
    routes = _routes_json()
    try:
        env = {**os.environ, "VEFR_ROUTES_JSON": routes}
        result = subprocess.run(
            ["node", str(HARNESS), str(ROOT)],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    finally:
        Path(routes).unlink(missing_ok=True)
    assert result.returncode == 0, (
        f"DOM harness failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "all harness checks passed" in result.stdout
    # The acceptance check for the 2026-09-03 'Journal card only
    # updates while Town is selected' bug. The harness stubs
    # /api/journal to increment a counter on every GET, and the
    # regression block at the bottom of the harness asserts that
    # whisper / strike / forge-keep events from any tab trigger
    # an automatic refetch. If those checks did not run, the
    # counter is missing from the run - this catches a regression
    # where someone deletes that block without re-adding coverage.
    assert "/api/journal refetch" in result.stdout or "refetch" in result.stdout, (
        "DOM harness ran without the journal-refresh regression block "
        "at the bottom of tests/fixtures/dom_harness.mjs. Re-add it or "
        "this guard will hide the 2026-09-03 bug class in the future."
    )
