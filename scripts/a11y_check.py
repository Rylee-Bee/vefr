"""Accessibility gate: run axe-core (vendored at scripts/vendor/axe.min.js,
MPL-2.0, see scripts/vendor/axe.min.js.LICENSE) over the woven single-file
player in real chromium. Fails on serious/critical violations; moderate and
below are printed for the record but do not fail the gate (the a11y matrix
in docs/guides/accessibility-contract.md remains the design authority).

usage: uv run python scripts/a11y_check.py <woven.html> [more.html ...]
"""

import sys
import pathlib

from playwright.sync_api import sync_playwright

AXE = pathlib.Path(__file__).resolve().parent / "vendor" / "axe.min.js"


def audit(page_path: str) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(pathlib.Path(page_path).resolve().as_uri())
        # enter past the title screen; blank setup = the remembered
        # offline choice, so the gate audits the real play surface.
        page.click("#ts-enter")
        page.wait_for_timeout(1000)
        if page.is_visible("#config"):
            page.click("#cfg-save")
            page.wait_for_timeout(400)
        page.add_script_tag(path=str(AXE))
        violations = page.evaluate(
            "() => axe.run(document, { resultTypes: ['violations'] })"
            ".then(r => r.violations.map(v => ({ id: v.id, impact: v.impact,"
            " nodes: v.nodes.length })))"
        )
        browser.close()
        return violations


def main(argv: list[str]) -> int:
    bad: list[tuple[str, dict]] = []
    for path in argv[1:]:
        for v in audit(path):
            print(f"{path}: {v['id']} [{v['impact']}] x{v['nodes']}")
            if v["impact"] in ("serious", "critical"):
                bad.append((path, v))
        print(f"{path}: audit complete")
    if bad:
        print(f"A11Y GATE FAILED: {len(bad)} serious/critical violation(s)")
        return 1
    print("a11y gate: no serious/critical violations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
