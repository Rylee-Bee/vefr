"""The rules bake: what weave_html puts in the woven file.

Part 3's contract, exactly three assertions:

1. a pack that declares NONE of flags/claims/people/rules bakes all
   four globals as the literal `null`, carries no rule data anywhere
   in the file, and leaves load_pack's keys exactly as they were;
2. BYTE-FOR-BYTE: weave the sample with the current template, then
   again with the rules block and the four new global lines removed
   from the template in memory. The brief's own escape hatch applies:
   those two removed pieces ARE bytes of the woven file, so the strings
   cannot be identical - the test asserts the EXACT difference instead
   (every differing byte is one of the removed pieces, baked), never a
   weaker approximation;
3. a pack that DOES declare the four keys bakes them (all four) and
   still validates green.

Deterministic: no clock, no randomness, no model call - weave_html is
a pure template fold.
"""

import json
import shutil
from pathlib import Path

from vefr import cli, maplab

SAMPLE = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"

# The four global lines part 3 added to web/packaged.html, verbatim -
# contiguous, so they can be lifted out as one piece.
GLOBALS_CHUNK = (
    "window.VEFR_RULES = {{rules_json}};\n"
    "window.VEFR_FLAGS = {{flags_json}};\n"
    "window.VEFR_CLAIMS = {{claims_json}};\n"
    "window.VEFR_PEOPLE = {{people_json}};\n"
)
ENGINE_START = "  // -- rules start --\n"
ENGINE_END = "  // -- rules end --\n"

# The four keys as a pack may declare them: each rule is one the
# validator accepts (the fixture used elsewhere declares the same set).
FLAGS = {"lit": "the torch is burning"}
CLAIMS = {"keeper-guards-gate": {"meaning": "the keeper guards the gate",
                                 "true": True}}
PEOPLE = {"keeper": {"believes": ["keeper-guards-gate"]}}
RULES = [
    {"id": "the-game-awakens",
     "when": {"starts": {}},
     "then": [{"set": "lit"}, {"say": "The rules are awake."}],
     "once": True},
    {"id": "keeper-is-near",
     "when": {"comes-near": {"who": "keeper", "distance": 3}},
     "then": [{"say": "Someone waits by the path."}],
     "once": True},
]


def _copy_sample(tmp_path: Path) -> Path:
    pack = tmp_path / "sample-world"
    shutil.copytree(SAMPLE, pack)
    return pack


def _declared(pack: Path, additions: dict) -> Path:
    cfg = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    cfg.update(additions)
    (pack / "world.json").write_text(json.dumps(cfg), encoding="utf-8")
    return pack


def _template() -> Path:
    return next(p for p in cli._template_candidates() if p.exists())


def test_a_pack_with_no_rules_bakes_null_and_no_rule_data(tmp_path):
    """Assertion 1: the light bake, byte for byte what it always was."""
    pack = _copy_sample(tmp_path)
    keys_before = set(maplab.load_pack(pack))
    assert not any(k in maplab.load_pack(pack)
                   for k in ("flags", "claims", "people", "rules"))

    html = cli.weave_html(pack)

    # All four globals present, each the literal null.
    for line in ("window.VEFR_RULES = null;",
                 "window.VEFR_FLAGS = null;",
                 "window.VEFR_CLAIMS = null;",
                 "window.VEFR_PEOPLE = null;"):
        assert line in html, line
    # Every placeholder consumed.
    for ph in ("{{rules_json}}", "{{flags_json}}",
               "{{claims_json}}", "{{people_json}}"):
        assert ph not in html, ph
    # No rule data anywhere: the JSON shapes of the four keys never
    # appear (the engine's own JavaScript uses unquoted keys, and the
    # placeholder word `rules` as JSON would always carry the colon).
    for key in ('"rules":', '"flags":', '"claims":', '"people":'):
        assert key not in html, key
    # load_pack hands back exactly the keys it did before the weave.
    keys_after = set(maplab.load_pack(pack))
    assert keys_after == keys_before


def test_byte_for_byte_only_the_rules_pieces_differ(tmp_path, monkeypatch):
    """Assertion 2: the brief's two weaves, and its exact difference.

    The brief asked for the two woven strings to be identical after
    removing "the rules block and the four new global lines". They
    cannot be: those very bytes live in the file. Per the brief's own
    escape hatch the assertion is NOT weakened to something vague -
    instead the exact difference is pinned: the woven file minus
    (the four baked global lines + the engine block, verbatim) equals
    the weave of the stripped template, byte for byte. The difference,
    in full, is reported in the commit message.
    """
    pack = _copy_sample(tmp_path)
    real = _template()
    full = real.read_text(encoding="utf-8")
    assert GLOBALS_CHUNK in full
    # The current template's weave.
    woven_full = cli.weave_html(pack)
    start = full.index(ENGINE_START)
    end = full.index(ENGINE_END) + len(ENGINE_END)
    assert start < end
    engine_chunk = full[start:end]
    stripped = full[:start] + full[end:]
    stripped = stripped.replace(GLOBALS_CHUNK, "", 1)
    tmp_tpl = real.with_name("packaged-rules-test-template.html")
    tmp_tpl.write_text(stripped, encoding="utf-8")
    monkeypatch.setattr(cli, "_template_candidates", lambda: [tmp_tpl])
    try:
        woven_stripped = cli.weave_html(pack)
    finally:
        tmp_tpl.unlink(missing_ok=True)

    # The four global lines bake to null for this pack (part 1); the
    # engine block carries no placeholder and lands verbatim.
    baked_globals = GLOBALS_CHUNK
    for ph in ("{{rules_json}}", "{{flags_json}}",
               "{{claims_json}}", "{{people_json}}"):
        baked_globals = baked_globals.replace(ph, "null")

    assert woven_full != woven_stripped, (
        "expected a difference: the removed pieces are part of the file")
    diff = woven_full
    for piece in (baked_globals, engine_chunk):
        assert diff.count(piece) == 1, f"the removed piece appears {diff.count(piece)} times"
        diff = diff.replace(piece, "", 1)
    # Every other byte matches: nothing else in the template or the
    # bake moved.
    assert diff == woven_stripped


def test_a_pack_with_rules_bakes_them_and_validates_green(tmp_path):
    """Assertion 3: declared keys bake (all four) and validate is green."""
    pack = _declared(_copy_sample(tmp_path),
                     {"flags": dict(FLAGS), "claims": dict(CLAIMS),
                      "people": dict(PEOPLE),
                      "rules": json.loads(json.dumps(RULES))})

    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []

    html = cli.weave_html(pack)
    # Not the null bake: all four keys are in the file.
    assert "window.VEFR_RULES = null" not in html
    assert "window.VEFR_RULES = [" in html
    for baked in ("the-game-awakens", "keeper-is-near",
                  "the torch is burning", "the keeper guards the gate",
                  '"believes"'):
        assert baked in html, baked
    # The rule DATA rides beside the engine, not instead of it.
    assert ENGINE_START in html and ENGINE_END in html


def _baked(html: str, name: str):
    """The JSON value baked onto `window.<name> = ...;` (one line)."""
    marker = f"window.{name} = "
    line = html[html.index(marker):].split("\n", 1)[0]
    return json.loads(line[len(marker):-1])


def test_entries_that_cannot_run_are_dropped_not_half_baked(tmp_path):
    """Part A: an unrunnable rule (or catalog entry) never reaches the
    ENGINE's baked catalogs. (The pack's raw world.json always rides
    along inside window.VEFR_WORLD - that is weave's own contract for
    every key, untouched here - so the check is on the rule globals
    the engine actually reads.)"""
    broken_rule = {"id": "never", "when": {"starts": {}},
                   "then": [{"wobble": "x"}]}
    no_id = {"when": {"starts": {}}, "then": [{"set": "lit"}]}
    pack = _declared(_copy_sample(tmp_path),
                     {"flags": dict(FLAGS), "claims": dict(CLAIMS),
                      "people": dict(PEOPLE),
                      "rules": RULES + [broken_rule, no_id]})

    html = cli.weave_html(pack)
    # The two good rules bake into the engine's list...
    baked_rules = _baked(html, "VEFR_RULES")
    assert [r["id"] for r in baked_rules] == ["the-game-awakens",
                                              "keeper-is-near"]
    # ...and neither broken entry does - not even partially.
    assert "never" not in json.dumps(baked_rules)
    assert "wobble" not in json.dumps(baked_rules)
    # A claim/flag/person entry in a bad shape is dropped the same way.
    pack2 = _declared(_copy_sample(tmp_path / "two"),
                      {"flags": {"lit": "the torch is burning",
                                 "broken-flag": 7},
                       "claims": {"broken": {"meaning": "no truth here"}},
                       "people": {"keeper": {"believes": "not-a-list"}},
                       "rules": []})
    html2 = cli.weave_html(pack2)
    assert _baked(html2, "VEFR_FLAGS") == {"lit": "the torch is burning"}
    assert _baked(html2, "VEFR_CLAIMS") == {}
    assert _baked(html2, "VEFR_PEOPLE") == {}
