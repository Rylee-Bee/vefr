"""The packaged file's pool-draw runtime, executed for real.

`ratatoskr weave --pool N` bakes `window.VEFR_POOL` into the
dist/<world>.html single file; the file's own poolDraw() then serves
lines when no live endpoint answers. Until now that runtime was only
ever exercised by hand - the DOM harness runs index.html, not the
packaged file (it pulls in canvas + the full app).

This test closes that gap the cheap-but-real way: it builds a real
packaged file through cmd_build_web with the generators monkeypatched
to canned outputs (no LLM), extracts the ACTUAL shipped pool block
from the built HTML - `const POOL_USED` through the end of
poolDraw(), between the file's own section markers - plus the baked
window.VEFR_POOL line, and hands both to tests/fixtures/pool_harness.mjs,
which executes them in a node vm sandbox and drives the semantics:
asked-for combo first, no repeats, cross-combo fallthrough, null when
spent, persistence across reload.

Known limit, stated plainly: this does NOT drive the packaged app's
button-level flow (click -> fetch fail -> catch -> poolDraw) in a
stub DOM - packaged.html's town canvas makes the full-app harness a
bigger job. The catch-block wiring is asserted statically instead.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "pool_harness.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


class _Canned:
    """Stand-in generation output: only the attrs build_pool reads."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def model_dump(self):  # noqa: D102 - mirrors the pydantic API
        return dict(self.__dict__)


@pytest.fixture()
def canned_generators(monkeypatch):
    """Deterministic generations: every combo fills, every line unique."""
    counter = {"n": 0}

    def rumor(phase):
        counter["n"] += 1
        return types.SimpleNamespace(
            speaker="Ember", whisper=f"canned whisper {phase} {counter['n']}",
            is_true=True)

    def line(phase, key=None):
        counter["n"] += 1
        return types.SimpleNamespace(
            speaker="Ember", line=f"canned line {phase} {key} {counter['n']}")

    def letter():
        counter["n"] += 1
        return types.SimpleNamespace(letter=f"canned letter {counter['n']}")

    def item():
        counter["n"] += 1
        return types.SimpleNamespace(
            model_dump=lambda: {"name": f"canned item {counter['n']}",
                                "kind": "trinket", "bond": [], "lore": "x"})

    from vefr import forge, generator, npc, stefna

    monkeypatch.setattr(generator, "generate_rumor", rumor)
    monkeypatch.setattr(npc, "generate_line", line)
    monkeypatch.setattr(stefna, "generate_letter", letter)
    monkeypatch.setattr(forge, "forge_item", item)


def _build_packaged_file(tmp_path, monkeypatch):
    """Build a real packaged file with a small canned pool baked in."""
    from vefr import cli

    out = tmp_path / "packaged.html"
    args = types.SimpleNamespace(
        pack="sample-world", out=str(out), pool=2, with_bundle=False,
        vault=None, journal=None, from_live=None)
    rc = cli.cmd_build_web(args)
    assert rc == 0, "cmd_build_web failed"
    return out.read_text(encoding="utf-8")


def _extract(html: str) -> str:
    """The shipped pool code: the VEFR_POOL line + the poolDraw block,
   taken verbatim from the built file between its own section markers."""
    pool_line = re.search(r"window\.VEFR_POOL = .*?;\n", html)
    block = re.search(
        r"// ---- the woven pool ----.*?(?=// ---- town ----)",
        html, re.DOTALL)
    if not (pool_line and block):
        raise AssertionError("packaged file's pool section markers not found")
    return pool_line.group(0) + "\n" + block.group(0)


def test_packaged_pool_draw_semantics(tmp_path, monkeypatch, canned_generators):
    html = _build_packaged_file(tmp_path, monkeypatch)

    # The bake: real (here, canned) generations landed in the file.
    assert "window.VEFR_POOL = {" in html
    assert '"rumor:dusk"' in html
    assert "canned whisper dusk" in html

    # The wiring: the rumor and npc catch blocks must reach the pool.
    assert "poolDraw('rumor:'" in html
    assert "poolDraw('npc:'" in html

    code = _extract(html)

    # The pool as baked: whisper combos have 2 entries (pool=2),
    # letter/forge specials have 3.
    pool_line = re.search(r"window\.VEFR_POOL = (.*?);\n", code)
    pool = json.loads(pool_line.group(1))
    assert pool["rumor:dusk"] and pool["letter"] and pool["forge"]

    spec = {"code": code, "pool": pool}
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(spec, f)
        spec_path = f.name
    try:
        result = subprocess.run(
            ["node", str(HARNESS), spec_path],
            capture_output=True, text=True, timeout=30,
            env={**os.environ},
        )
    finally:
        Path(spec_path).unlink(missing_ok=True)
    assert result.returncode == 0, (
        f"pool harness failed:\n{result.stdout}\n{result.stderr}")
    assert "pool harness passed" in result.stdout


def test_packaged_carries_the_surface_costume(tmp_path, monkeypatch, canned_generators):
    """The combat costume rides in the packaged file too - the web UI
    half landed in 06eed41; the packaged half was the gap. The built
    file must carry the HP bar, the encounter prompt, the verb row,
    and the data-surface branch that shows all of it only for
    combat-surface packs."""
    html = _build_packaged_file(tmp_path, monkeypatch)

    # Markup.
    assert 'id="hud-hp"' in html and 'id="hud-hp-fill"' in html
    assert 'id="encounter-prompt"' in html
    assert 'id="verb-row"' in html and 'data-verb="attack"' in html
    # The surface comes from the pack at play time, not from the
    # template - a plain pack never sees the costume.
    assert "setAttribute('data-surface'" in html
    assert 'body[data-surface="plain"] .hud-hp' in html
    assert 'body[data-surface="investigation"] .verb-row' in html
    # The verbs record honestly, locally - same no-failure contract
    # as the server route, minus the server.
    assert "localStorage.getItem(COMBAT_KEY" in html
    # Engine neutrality: the costume never names a pack's phase
    # vocabulary. (The live app once grew a lines dict keyed by the
    # author's own phase names; the packaged file must not repeat it.)
    template = (Path(__file__).resolve().parents[1] / "web" / "packaged.html").read_text(encoding="utf-8")
    for phase_key in ("doubts", "feared", "awed"):
        assert f"'{phase_key}'" not in template, (
            f"packaged template must not hardcode phase name '{phase_key}'"
        )
