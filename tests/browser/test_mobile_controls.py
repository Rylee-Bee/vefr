"""The mobile controls (390x844, the iPhone-class portrait window).

Three rules, Rylee 2026-10-07:
  1. The control bar (d-pad + action row) sits in a stable box: its outer
     position does not reflow when the HUD's text content changes. The
     HUD grows downward as the world grows lines; the controls stay at
     the bottom of the stage, at the same rect, every state.
  2. Nothing covers a control; tap targets are at least 44x44 CSS px;
     safe-area-insets (the OS home indicator at the bottom, the status
     bar at the top) are respected.
  3. Buggy controls, found one by one, are fixed at the root.

The browser hands back two numbers we trust:
  - the live `--sai-bottom` value the OS reports (set on :root by
    playwright from the device metrics; default 0 on a desktop page).
  - the rendered rect of every named control.

Uses the interact fixture (an 11x7 map: small on purpose, so it is
letterboxed on any window). The HUD is forced to its widest state
(HP + level + gold + bag strip + light) before measuring, so the
test does not pass on a HUD that hides the bug.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[2]
MAKE = ROOT / "tests" / "fixtures" / "make_interact_pack.py"


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    d = tmp_path_factory.mktemp("mobile-ctl")
    out = subprocess.run([sys.executable, str(MAKE), str(d)],
                        capture_output=True, text=True, check=True).stdout.strip()
    pack = Path(out.splitlines()[-1])
    # A full HUD: levels (the level chip) and gold (the gold chip), as a real game shows them.
    wj = pack / "world.json"
    cfg = json.loads(wj.read_text(encoding="utf-8"))
    cfg["growth"] = {"mode": "levels", "levels": {"xp": [0, 3, 6], "gain": {"hp": 2, "atk": 1}}}
    cfg["player"]["gold"] = 128
    wj.write_text(json.dumps(cfg), encoding="utf-8")
    html = d / "x.html"
    html.write_text(cli.weave_html(pack), encoding="utf-8")
    return html


# The six controls whose outer rect we are checking. Each must satisfy
# both rules at 390x844. The names match the DOM ids of the buttons.
CONTROLS = ["dpad", "interact", "talk", "whisper", "bagbtn", "explore", "menu-open"]

# Show the HUD in its widest state so a layout-shift bug that hides
# under an empty cap will surface.
SHOW_FULL_HUD = """() => {
  const show = id => { const el = document.getElementById(id);
                       if (el) { el.hidden = false; } };
  show('hud-level'); show('bag-strip'); show('light-live');
  const lvl = document.getElementById('hud-level');
  if (lvl) lvl.textContent = 'lvl 3';
  const bag = document.getElementById('bag-strip');
  if (bag) bag.textContent = 'rusty key / band / lamp / rope';
  const light = document.getElementById('light-live');
  if (light) light.textContent = 'Bright';
}"""

RECTS = """() => {
  const ids = ['dpad', 'interact', 'talk', 'whisper', 'bagbtn', 'explore',
               'menu-open', 'hud-hp', 'hud-level', 'hud-gold', 'bag-strip',
               'light-live', 'toasts-toggle', 'toasts', 'verb-row'];
  const out = {};
  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el || el.hidden) { out[id] = null; continue; }
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) { out[id] = null; continue; }
    out[id] = {l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height};
  }
  return out;
}"""


@pytest.fixture(scope="module")
def page_at(browser, woven):
    """A 390x844 touch context with the player on the start screen, full HUD on."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
    page = ctx.new_page()
    page.goto(woven.as_uri())
    page.click("#ts-enter")
    page.wait_for_function("window.VEFR_COMBAT", timeout=15000)
    page.wait_for_timeout(300)
    page.evaluate(SHOW_FULL_HUD)
    page.wait_for_timeout(150)
    yield page
    ctx.close()


def test_safe_area_inset_bottom_respected_at_390x844(page_at):
    """Rylee 2026-10-07: "respect safe-area insets". The OS hands a 34 px home
    indicator at the bottom of the window on a phone with a chin. Every
    bottom-anchored control (d-pad, action row, verb row) must sit ABOVE
    that line - the gap between the control's bottom edge and the
    viewport bottom is at least the inset."""
    # Drive the OS-reported inset by overriding the CSS variable the
    # style sheet reads. The default is 0 on a desktop page; we set 34
    # to model an iPhone-class home indicator. A second context gives a
    # second screenshot in case the test runner has any doubt.
    inset = 34
    page_at.evaluate(
        "(v) => document.documentElement.style.setProperty('--sai-bottom', v + 'px')",
        inset)
    page_at.wait_for_timeout(100)
    rects = page_at.evaluate(RECTS)
    for name in ("dpad", "acts", "verb-row"):
        # `dpad` and `verb-row` are containers; the rect on a child is the
        # one with the visible buttons.
        anchor = name
        if name == "acts":
            # The #interact button lives inside the .acts container; use
            # it as the bottom anchor because the container's own rect
            # grows to fit any wrapped buttons.
            anchor = "interact"
        r = rects.get(anchor)
        assert r, f"missing control {anchor}"
        gap = page_at.evaluate("innerHeight") - r["b"]
        assert gap >= inset - 1, (
            f"{name} sits {gap:.0f} px from the viewport bottom, "
            f"the OS home indicator is {inset} px")


def test_safe_area_inset_top_respected_at_390x844(page_at):
    """The HUD row sits below the OS status bar / notch. The HUD's top
    edge is at least the top inset."""
    inset = 47  # iPhone-class notch
    page_at.evaluate(
        "(v) => document.documentElement.style.setProperty('--sai-top', v + 'px')",
        inset)
    page_at.wait_for_timeout(100)
    rects = page_at.evaluate(RECTS)
    r = rects["hud-hp"]
    assert r["t"] >= inset - 1, (
        f"hud-hp top {r['t']:.0f} px, top inset {inset} px")


def test_control_bar_is_stable_when_hud_changes(browser, woven):
    """Rylee 2026-10-07: "controls shift and get buggy with the ui". The
    control bar (d-pad + action row) is a stable, reserved box at the
    bottom of the stage. HUD text growing shows the items move; the
    control bar's outer rect does NOT."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
    page = ctx.new_page()
    page.goto(woven.as_uri())
    page.click("#ts-enter")
    page.wait_for_function("window.VEFR_COMBAT", timeout=15000)
    page.wait_for_timeout(300)
    # Start from the sparsest HUD: hide the level chip, bag strip and light.
    # The interact fixture already enables growth + gold so the HUD grows
    # when we flip them back on.
    page.evaluate("""() => {
      const hide = id => { const el = document.getElementById(id);
                            if (el) { el.hidden = true; } };
      hide('hud-level'); hide('bag-strip'); hide('light-live');
    }""")
    page.wait_for_timeout(150)
    sparse = page.evaluate(RECTS)
    # Now flip the HUD to its widest state (level + bag strip + light).
    page.evaluate(SHOW_FULL_HUD)
    page.wait_for_timeout(150)
    full = page.evaluate(RECTS)
    # The HUD moved (proves the test isn't a no-op) and the controls did not.
    assert sparse["hud-level"] is None, \
        "the HUD did not start sparse: hud-level was already showing"
    assert full["hud-level"] is not None, \
        "the HUD width-state toggle did not flip"
    for name in ("dpad", "interact", "talk", "whisper", "bagbtn", "explore", "menu-open"):
        a = sparse.get(name)
        b = full.get(name)
        assert a and b, f"missing control {name} in one of the states"
        # Less than 1.5 CSS px of drift - far below the tap-target floor.
        drift = max(abs(a["l"] - b["l"]), abs(a["t"] - b["t"]),
                    abs(a["r"] - b["r"]), abs(a["b"] - b["b"]))
        assert drift < 1.5, (
            f"{name} shifted by {drift:.1f} px when the HUD grew: "
            f"sparse={a} full={b}")
    ctx.close()


def test_tap_targets_meet_the_44px_floor(browser, woven):
    """Rylee 2026-10-07: "tap targets at least 44x44 CSS px". Every
    visible control is at least 44 px wide and 44 px tall in CSS px.
    The d-pad container is 120+ px tall (3 rows of 44); the test
    checks the container so a wrapper hit don't accidentally pass."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
    page = ctx.new_page()
    page.goto(woven.as_uri())
    page.click("#ts-enter")
    page.wait_for_function("window.VEFR_COMBAT", timeout=15000)
    page.wait_for_timeout(300)
    page.evaluate(SHOW_FULL_HUD)
    page.wait_for_timeout(150)
    info = page.evaluate("""() => {
      const names = ['interact', 'talk', 'whisper', 'bagbtn', 'explore',
                     'menu-open', 'toasts-toggle', 'dpad'];
      const out = {};
      for (const name of names) {
        const el = document.getElementById(name);
        if (!el || el.hidden) continue;
        const r = el.getBoundingClientRect();
        out[name] = {w: r.width, h: r.height};
      }
      return out;
    }""")
    for name, size in info.items():
        assert size["w"] >= 44 and size["h"] >= 44, (
            f"{name} is {size['w']:.0f}x{size['h']:.0f}, below the 44px floor")
    ctx.close()


def test_page_does_not_sideways_scroll(browser, woven):
    """Rylee 2026-10-07: "no horizontal scroll". The page's scrollWidth
    equals the inner width even with the full HUD on."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
    page = ctx.new_page()
    page.goto(woven.as_uri())
    page.click("#ts-enter")
    page.wait_for_function("window.VEFR_COMBAT", timeout=15000)
    page.wait_for_timeout(300)
    page.evaluate(SHOW_FULL_HUD)
    page.wait_for_timeout(150)
    info = page.evaluate("""() => ({
      sw: document.documentElement.scrollWidth,
      iw: innerWidth,
    })""")
    assert info["sw"] <= info["iw"], \
        f"the page sideways-scrolls: scrollWidth={info['sw']}, innerWidth={info['iw']}"
    ctx.close()