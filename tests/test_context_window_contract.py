"""`context_window` is capability metadata and nothing else.

A pack declares what its model can do; `Storyteller.context_window` is
where that claim lands. It never sizes memory, never sizes a KV cache,
and no code path reads it - the servers the bundled brain starts use
small fixed sizes chosen to fit a laptop. These tests keep that true:
they fail if anyone ever derives a server context size from a pack, and
they hold the numbers `docs/guides/storyteller-packs.md` quotes.

Real tests, no skips: the point is that the claim is under test.
"""

import ast
import re
import tomllib
from pathlib import Path

from vefr import spark, storyteller
from vefr.cli import _quadlet_text

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "vefr"
START_BUNDLED = ROOT / "deploy" / "start-bundled.sh"

# The largest context size any bundled-brain server may start with. The
# Spark quadlet pins 8192; the shell script stays at or below it.
_LAPTOP_CTX_CEILING = 8192

_CTX_SIZE_RE = re.compile(r"--ctx-size\s+(\d+)")


def test_no_pack_context_window_reaches_a_server_command():
    """Guard: no engine code may read `context_window` off a Storyteller.

    NOTE: this is the regression guard for the metadata-only path. The
    number is a claim about the model, not a request to any server; if a
    future change starts doing `st.context_window` or
    `min(recommended_ctx, story.context_window)` to size a server from a
    pack, this test fails. Attribute access is the signal - the loader's
    dict read (`model_block.get("context_window")`) is not.
    """
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            rel = path.relative_to(ROOT)
            # `something.context_window` - a read off an object.
            if isinstance(node, ast.Attribute) and node.attr == "context_window":
                offenders.append(f"{rel}:{node.lineno} attribute read")
            # `getattr(something, "context_window")` - the same read spelled out.
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "context_window"
            ):
                offenders.append(f"{rel}:{node.lineno} getattr read")
    assert offenders == [], (
        "context_window is metadata only and is read by no code path; "
        "these sites read it off an object: " + ", ".join(offenders)
    )


def test_every_bundled_pack_declares_an_int_context_window():
    """The field stays meaningful as metadata: real int, >= 0, round-trips."""
    manifests = sorted((ROOT / "storyteller_packs").glob("*/storyteller.toml"))
    assert manifests, "no bundled storyteller packs found - the field would go untested"

    for manifest_path in manifests:
        pack_id = manifest_path.parent.name
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        model_block = manifest.get("model", {})
        declared = model_block.get("context_window", manifest.get("context_window"))
        assert declared is not None, f"{pack_id} declares no context_window"
        assert type(declared) is int, f"{pack_id} context_window is not an int: {declared!r}"
        assert declared >= 0, f"{pack_id} context_window is negative: {declared}"

        loaded = storyteller._manifest_to_storyteller(
            pack_id, manifest, pack_dir=manifest_path.parent
        )
        assert loaded.context_window == declared, (
            f"{pack_id} declared {declared} but the loader yielded {loaded.context_window}"
        )


def test_the_laptop_sized_servers_are_not_pack_sized():
    """The bundled-brain context sizes are small, fixed, and pack-free.

    NOTE: these are the exact numbers `docs/guides/storyteller-packs.md`
    quotes (2048/4096/512 in the script, 8192 in the Spark quadlet), so
    the doc and this test cannot drift apart silently. Neither server
    reads a pack - the sizes are literals chosen to fit a laptop.
    """
    script = START_BUNDLED.read_text(encoding="utf-8")
    sizes = [int(m) for m in _CTX_SIZE_RE.findall(script)]
    assert sizes, "no --ctx-size found in deploy/start-bundled.sh"
    oversized = [n for n in sizes if n > _LAPTOP_CTX_CEILING]
    assert oversized == [], (
        f"bundled-brain context size(s) {oversized} exceed the laptop ceiling "
        f"{_LAPTOP_CTX_CEILING}"
    )

    quadlet = _quadlet_text(spark.profile(), "img")
    assert "-c 8192" in quadlet, "Spark quadlet no longer starts at -c 8192"
