"""The interface lives inside the game's stage (docs/plans/interface/PLAN.md). FROZEN CONTRACT.

Rylee, 2026-10-04: "anything running 'inside the game' [should] be in a themed ui for that game and only controls and
such ... the map section icons go into the 'background' of the page." Today the HUD and buttons are placed against the
whole browser window, so on a small map they float on the dark page beside the drawn map.

The contract:
  - `window.VEFR_STAGE` = {x, y, w, h} (CSS pixels, in the viewport): the rectangle of the drawn map, clipped to the
    window. A map bigger than the window gives the window itself.
  - Every visible HUD piece and control (the health/level/gold panels, the bag strip, the Menu button, the message
    panels, the Interact button and the small action buttons, and the touch d-pad when it is shown) lies inside that
    rectangle, within 1 pixel, at every size below, desktop and phone.
  - Nothing sideways-scrolls the page.
Uses the interact fixture (an 11x7 map: small on purpose, so it is letterboxed on any window).
"""

import socket  # noqa: F401  (kept for parity with the sibling files)
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[2]
MAKE = ROOT / "tests" / "fixtures" / "make_interact_pack.py"

SIZES = [(1920, 1080, False), (1366, 768, False), (1280, 720, False), (1024, 600, False),
         (844, 390, True), (390, 844, True), (360, 640, True)]

COLLECT = """() => {
  const sel = '#play .hud .glass, #play .hud button, #play .gbtn, #play .toasts p, #play .toasts-toggle, #dpad button, #play #interact, #play .actions button';
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || el.hidden || el.closest('[hidden]')) continue;
    if (el.classList.contains('sr-only') || el.closest('.sr-only')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    out.push({id: el.id || el.className.toString().split(' ')[0] || el.tagName, l: r.left, t: r.top, r: r.right, b: r.bottom});
  }
  return {stage: window.VEFR_STAGE || null, els: out, sw: document.documentElement.scrollWidth, iw: innerWidth};
}"""


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    d = tmp_path_factory.mktemp("stage")
    out = subprocess.run([sys.executable, str(MAKE), str(d)], capture_output=True, text=True, check=True).stdout.strip()
    html = d / "stage.html"
    html.write_text(cli.weave_html(Path(out.splitlines()[-1])), encoding="utf-8")
    return html


@pytest.mark.parametrize("w,h,touch", SIZES)
def test_every_control_is_inside_the_stage(browser, woven, w, h, touch):
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    page = ctx.new_page()
    try:
        page.goto(woven.as_uri())
        page.click("#ts-enter")
        page.wait_for_function("window.VEFR_COMBAT", timeout=15000)
        page.wait_for_timeout(500)
        info = page.evaluate(COLLECT)
        st = info["stage"]
        assert st is not None, "window.VEFR_STAGE is not published"
        assert st["w"] > 50 and st["h"] > 50
        assert info["sw"] <= info["iw"], "the page scrolls sideways"
        outside = [e for e in info["els"]
                   if e["l"] < st["x"] - 1 or e["t"] < st["y"] - 1
                   or e["r"] > st["x"] + st["w"] + 1 or e["b"] > st["y"] + st["h"] + 1]
        assert not outside, f"{len(outside)} piece(s) outside the stage {st}: {outside[:4]}"
    finally:
        ctx.close()
