"""The dev board, executed for real.

web/board.js is shipped JS - the Dev zone's board is part of the
served engine UI. The shipped-JS test pattern (test_web_packaged.py,
test_prefs.py) treats the JS itself as the source of truth: the
harness (tests/fixtures/board_harness.mjs) executes board.js in a
node vm sandbox with a stubbed DOM, localStorage, and fetch, and
drives the contract:

  - generateStore is deterministic for a given world + seed
  - voices come from the pack's own speakers; a speakerless world
    falls back to the seeded neutral pool (the bone-strip invariant:
    no canon string appears in a generated store)
  - init() renders the columns and persists under vefr-board-cards
  - move() re-homes a card across columns, stamps it edited, and
    persists; a fresh boot loads the store instead of regenerating
  - move() refuses unknown ids and unknown columns
  - selecting a card fills and unhides the right rail
  - "try it" answers honestly when the engine is offline and shows
    the response JSON when it is not

The second test checks the chrome wiring in web/index.html: the
Board tab exists in the Dev zone, the view-board section exists, and
board.js + board.css are loaded - the exact wiring a missing edit
would silently drop.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "board_harness.mjs"
BOARD_JS = ROOT / "web" / "board.js"
INDEX_HTML = ROOT / "web" / "index.html"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def test_board_js_contract():
    assert BOARD_JS.exists(), f"board.js missing at {BOARD_JS}"
    result = subprocess.run(
        ["node", str(HARNESS), str(BOARD_JS)],
        capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        pytest.fail(
            f"board harness failed:\nSTDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    assert "ALL PASS" in result.stdout, (
        f"harness did not report ALL PASS:\n{result.stdout}\n{result.stderr}"
    )


def test_board_wired_into_chrome():
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'data-view="board"' in html, "Dev tablist is missing the Board tab"
    assert 'id="view-board"' in html, "view-board section missing from index.html"
    assert 'id="board-rail"' in html, "right-rail aside missing from index.html"
    for col in ("whispers", "voices", "forge", "bell"):
        assert f'id="board-{col}"' in html, f"board-{col} column holder missing"
    assert 'src="/static/board.js"' in html, "board.js script tag missing"
    assert 'href="/static/board.css"' in html, "board.css stylesheet link missing"
    assert "old-name:board" in html, "tabs must dispatch old-name:board for lazy boot"
    # The board must not leak outside the Dev zone: it lives only in
    # its own hidden view section, not in the always-on markup.
    assert html.count("board-container") == 1, "board container should appear exactly once"
    # The drag layer: Sortable is vendored and loaded before board.js;
    # the keyboard re-home row + live status live in the rail markup.
    assert 'src="/static/vendor/Sortable.min.js"' in html, (
        "vendored Sortable script tag missing (drag layer)"
    )
    assert html.index('src="/static/vendor/Sortable.min.js"') < html.index('src="/static/board.js"'), (
        "Sortable must load before board.js"
    )
    assert 'id="board-status"' in html, "aria-live move status missing"
    assert 'id="board-move-forge"' in html, "keyboard re-home buttons missing"
    assert 'id="rail-chat-send"' in html, "smith draft send button missing"
    assert 'disabled' not in (html.split('id="rail-draft"')[1][:200]), (
        "the draft box must be live now - it wires to /api/builder/chat"
    )
    assert (Path(__file__).resolve().parents[1] / "web" / "vendor" / "Sortable.min.js").exists(), (
        "vendored Sortable.min.js file missing"
    )
