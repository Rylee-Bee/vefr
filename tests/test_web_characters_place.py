"""The Folks room's Keep -> preview -> Put in the game flow, run for real.

web/js/rooms/characters.js used to send a suggested face straight to the
vault. Now Keep asks POST /api/builder/character/place for a preview
(nothing written), the room shows a card with the face, where they'd
stand and their first line, and only "Put in the game" performs the
write. This test executes the REAL web/js/api.js and
web/js/rooms/characters.js in a node vm with a stubbed DOM and fetch,
then drives the flow (tests/fixtures/characters_harness.mjs).

The harness is a node-vm harness like board_harness.mjs, not a jsdom
one: jsdom is not installed in this environment and there is no network
to fetch it, so a jsdom harness would error here. This one runs.

Skips gracefully if node isn't installed - the same zero-setup promise
as the repo's other web tests.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "characters_harness.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def test_keep_previews_then_put_in_the_game_writes():
    """The whole contract, pinned in the harness:

    - Keep issues the place request with preview:true (and never force)
    - the preview card shows the name, the role and the first seed line
    - Put in the game issues the same request with preview:false
    - a 422 shows the server's own plain sentence on the page
    - a 409 offers the replace step (force:true) in plain words
    - the vault keep still works as its own explicit step
    """
    result = subprocess.run(
        ["node", str(HARNESS), str(ROOT)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        pytest.fail(f"characters harness failed:\n{result.stdout}\n{result.stderr}")
    assert "ALL PASS" in result.stdout, result.stdout
