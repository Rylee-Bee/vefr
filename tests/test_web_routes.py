"""Every API URL the web layer fetches must be a route the server serves.

The class-level fix for the stefna-tab incident: the server renamed
a route, the page kept fetching the old one, and the DOM harness's
stub faked the stale URL - so the suite stayed green while live
play 404'd. See docs/guides/one-source-of-routes.md.

Known limit: URLs assembled at runtime from pieces show up in
source as the bare prefix '/api/'; those are skipped here and are
the harness-hardening follow-up in ROADMAP.
"""

import re
from pathlib import Path

from vefr.main import app

WEB = Path(__file__).resolve().parents[1] / "web"


def _served_api_paths() -> set[str]:
    return {
        route.path
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/")
    }


def _fetched_literals() -> set[str]:
    found: set[str] = set()
    files = sorted(WEB.glob("*.js")) + [WEB / "index.html"]
    for f in files:
        text = f.read_text(encoding="utf-8")
        found |= set(re.findall(r"""['"](/api/[A-Za-z0-9_\-/{}]*)['"]""", text))
    return found


def test_every_url_the_web_fetches_is_a_real_route():
    served = _served_api_paths()
    assert served, "the server exposes no /api routes - the guard is blind"
    bad = []
    for literal in sorted(_fetched_literals()):
        # A bare '/api/' prefix comes from runtime-assembled URLs
        # (e.g. '/api/' + target + '/undo') and says nothing on its own.
        if literal == "/api/":
            continue
        if literal in served:
            continue
        # A trailing slash means a dynamic tail is appended at runtime;
        # the route exists if some served path starts with the prefix.
        if literal.endswith("/") and any(p.startswith(literal) for p in served):
            continue
        bad.append(literal)
    assert not bad, (
        f"the web layer fetches routes the server does not serve: {bad}. "
        "Update web/ to match src/vefr/main.py, or the live UI 404s "
        "while tests stay green - the stefna-tab incident."
    )
