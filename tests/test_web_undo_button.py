"""The Desk's Undo last edit button, run for real in a node vm.

web/js/rooms/workshop.js now offers **Undo last edit** on the Desk, in
the weave row beside **Play it here**. It posts to
/api/builder/edits/undo with `{"name": null}` (the route falls back to
the active world - exactly what the Folks room already sends for a
placement) and writes the answer into its polite live region
(#ws-undo-status, role="status", aria-live="polite"). This test executes
the REAL web/js/api.js and web/js/rooms/workshop.js in a node vm with a
stubbed DOM and fetch, then presses the button
(tests/fixtures/undo_harness.mjs).

Pinned by the harness:

- a POST to /api/builder/edits/undo with a JSON body was made
- on 200 the route's own sentence appears verbatim in the status
  region, and the Desk reloads
- on 404 the message is friendly (the route's words), not an error,
  and nothing else is refetched
- on any other failure the sentence is plain - never "409 Conflict"
- the button is disabled while a request is in flight and re-enabled
  after every answer

Skips gracefully if node isn't installed - the same zero-setup promise
as the repo's other web tests.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "undo_harness.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def test_the_desk_undo_button_posts_and_answers_in_its_status_region():
    """The whole client contract, pinned in the harness (see above)."""
    result = subprocess.run(
        ["node", str(HARNESS), str(ROOT)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        pytest.fail(f"undo harness failed:\n{result.stdout}\n{result.stderr}")
    assert "ALL PASS" in result.stdout, result.stdout
