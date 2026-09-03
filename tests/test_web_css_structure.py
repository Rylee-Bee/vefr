"""CSS structural checks the DOM harness cannot catch.

The harness executes the JS in a node vm with a stubbed DOM - it
verifies behavior the controller drives, but it cannot observe CSS
features that only a browser engine resolves: media-query
conditions, computed layout, paint, focus rings, real pointer
geometry. This file catches the failure classes where JS-hidden
truth and CSS-visible truth can drift apart.

Each test here asserts an invariant about web/index.html itself
(via static reads) plus an invariant we can verify in the harness.
The point isn't to substitute for a browser - it's to make the
common CSS failure modes _loud in pytest_ instead of silent in
production. The CI scripts/ where the browser renders
gatus-probed endpoints is the runtime source of truth.
"""
from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
INDEX = WEB / "index.html"


def _read() -> str:
    return INDEX.read_text(encoding="utf-8")


def test_no_var_substitution_in_media_query_conditions():
    """`var()` is invalid inside media-query conditions. Every browser
    silently drops the entire rule block when it sees one, so the
    whole free-dock structural enablement would never apply.

    The single known instance was `@media (min-width: var(--free-dock-breakpoint))`
    in the wide-layout block. It must stay fixed: a literal `1180px`.
    The matching CSS variable on :root remains so JS can read it
    via getComputedStyle (var() works fine for non-condition uses).
    """
    text = _read()
    # Match every @media block whose condition uses var(...). The
    # pattern tolerates whitespace inside the parens.
    hits = re.findall(r"@media[^{]*var\s*\([^)]+\)[^{]*\{", text)
    assert not hits, (
        "var() inside @media conditions is invalid CSS; all browsers "
        "drop the rule. Use a literal breakpoint and keep the var for "
        "getComputedStyle-only consumers. Found:\n  " + "\n  ".join(hits)
    )


def test_free_dock_wide_media_query_uses_literal_breakpoint():
    """Regression for the wide-screen free-dock gate. The CSS rule
    enabling free-dock structural behavior must use a numeric literal
    in its condition, AND must equal the value both the :root
    custom property and the JS FREE_BREAKPOINT constant resolve to.
    Drift between any of the three breaks wide-layout behavior.
    """
    text = _read()

    # The CSS :root variable.
    css_var = re.search(
        r"free-dock-breakpoint:\s*([0-9]+)px", text
    )
    assert css_var, "--free-dock-breakpoint must be declared on :root"
    assert css_var.group(1) == "1180", (
        f"--free-dock-breakpoint expected 1180px, got {css_var.group(1)}px"
    )

    # The @media condition must be a literal 1180px. We anchor the
    # match to the free-dock block (whose body contains 'is-keyboard-moving'
    # or '.panel-frame' - words that uniquely belong to this block) to
    # avoid false matches against the unrelated 760px composed-grid
    # @media query.
    media = re.search(
        r"@media\s*\(min-width:\s*([0-9]+)px\s*\)\s*\{"
        r"(?=[^{}]*(?:is-keyboard-moving|panel-frame))",
        text,
    )
    assert media, "@media (min-width: ...) free-dock block must exist"
    assert media.group(1) == "1180", (
        f"free-dock @media expected 1180px, got {media.group(1)}px"
    )

    # The JS FREE_BREAKPOINT must fall back to a numeric value (1180)
    # when the CSS variable is absent - that's the single source of
    # truth in code. parseInt('1180px') is the parseable form here.
    # The parseInt arg here contains commas (parseInt(value, 10))
    # plus a quoted property name, so a `[^)]+` body isn't well-suited;
    # the lazy `[\s\S]+?` form finds the matching `)` cleanly.
    js_fallback = re.search(
        r"FREE_BREAKPOINT\s*=\s*parseInt\([\s\S]+?\)\s*\|\|\s*(\d+)",
        text,
    )
    assert js_fallback, (
        "JS FREE_BREAKPOINT must declare a numeric fallback after "
        "the parseInt(...) call (e.g. `parseInt(...) || 1180`)."
    )
    assert js_fallback.group(1) == "1180", (
        f"JS FREE_BREAKPOINT fallback expected 1180, got {js_fallback.group(1)}"
    )

    # All three numbers must agree.
    assert (
        css_var.group(1)
        == media.group(1)
        == js_fallback.group(1)
        == "1180"
    ), "free-dock breakpoint drifted between CSS variable, @media, and JS"


def test_compact_density_does_not_undercut_44px_targets():
    """The inclusive-forward contract requires interactive targets
    >= 44x44 CSS px (AGENTS.md Always rule). The compact-density pref
    visually compresses padding but must not drop min-height below
    the contract.

    This is a regression for the case where a future refactor moves
    compact-density padding back to min-height rather than padding.
    The current shipped rule is the two-line form below at line ~223;
    both targets and the contract line stay readable for review.
    """
    text = _read()
    # Compact-density rule for the buttons exposed in tabs / zone
    # buttons / phase rail. min-height must stay >= 44px (the spec
    # is `min-height: 36px` in compact, but the rule is allowed to
    # drop padding - and not the min-height - so 44 wins).
    # The selector list is multi-selector with one body; rather than
    # parsing braces, scan the whole file for any min-height: Npx
    # that appears after a density=compact selector and before the
    # next density=compact / unrelated block.
    matches = re.findall(
        r"\[data-prefs[^]]*density=compact[^]]*\][^{}]*\{([^}]+)\}",
        text,
    )
    assert matches, "compact-density rules must exist"
    for body in matches:
        for h in re.findall(r"min-height:\s*([0-9]+)px", body):
            assert int(h) == 0 or int(h) >= 44, (
                f"compact-density min-height={h}px violates the >= 44px "
                "target contract. Compact mode should compress padding, "
                "not the hit-target."
            )

    # Independent sanity check: no compact-density selector block may
    # set min-height lower than 44px as a literal. This catches a
    # refactor that reintroduces the 36px rule under density.
    for block in re.findall(
        r"\[data-prefs[^]]*density=compact[^]]*\][^{}]*\{[^}]*\}",
        text,
    ):
        for h in re.findall(r"min-height:\s*([0-9]+)px", block):
            assert int(h) == 0 or int(h) >= 44, (
                "compact-density hit-target under 44px is a contract "
                f"regression (got {h}px)"
            )
