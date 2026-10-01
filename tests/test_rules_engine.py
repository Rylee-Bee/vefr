"""The rules engine, executed for real.

Task 2 of the rules work (design/rules-when-then.md): the engine is
pure functions - events in, actions out - and lives in
web/packaged.html between its own markers, right after pickCell. This
module extracts that exact text, runs it in a node vm sandbox with no
npm packages (the same close-the-gap move as
tests/test_web_pack_tiles.py), and drives it over written case files:
the no-rules compatibility case, `once` (default true) and `once`
false, no chains, every false condition blocking, beliefs with their
sources, the action round-trip, and the one-sentence why.

Skips gracefully when node is missing - this repo's engine tests never
require it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGED = ROOT / "web" / "packaged.html"
HARNESS = Path(__file__).resolve().parent / "fixtures" / "rules_harness.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)

SIX_EVENTS = [
    ["starts", {}],
    ["enters", {"place": "harbour"}],
    ["comes-near", {"who": "cat", "distance": 1}],
    ["opens", {"what": "chest"}],
    ["picks-up", {"what": "key"}],
    ["uses-with", {"item": "key", "with": "panel"}],
]


def _block() -> str:
    """The shipped rules block, from marker to marker."""
    src = PACKAGED.read_text(encoding="utf-8")
    start = src.index("// -- rules start --")
    end = src.index("// -- rules end --")
    assert end > start, "the rules markers are out of order"
    return src[start:end]


def _run(tmp_path: Path, spec: dict) -> str:
    """Write the case file, run the harness, return its stdout."""
    case_file = tmp_path / "rules_cases.json"
    case_file.write_text(json.dumps(spec), encoding="utf-8")
    result = subprocess.run(
        ["node", str(HARNESS), str(PACKAGED), str(case_file)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"rules harness failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def test_extraction_returns_the_real_shipped_block():
    """The block is non-empty, brackets exactly one global, and is
    pure JS: nothing deterministic surfaces may reach into it."""
    src = PACKAGED.read_text(encoding="utf-8")
    block = _block()
    assert block.strip(), "the rules block is empty"
    # A pure-JS marker inside the block: the engine itself. The block
    # ends right where the end marker begins (slice excludes it).
    assert "window.VEFR_RULES_ENGINE = (function ()" in block
    assert block.rstrip().endswith("})();")
    assert src[src.index("// -- rules end --"):].startswith("// -- rules end --")
    # It sits right after pickCell, so the extraction pattern is
    # the same one tests/fixtures/tiles_harness.mjs already uses.
    assert src.index("// -- pickCell end --") < src.index("// -- rules start --")
    # No clock, no randomness, no DOM, no fetch can reach in.
    for forbidden in ("Math.random", "Date(", "performance", "fetch(",
                      "document.", "localStorage", "setTimeout"):
        assert forbidden not in block, f"{forbidden!r} found in the rules block"


def test_no_rules_pack_is_compatible_on_every_event(tmp_path: Path):
    """pack.rules missing or []: a usable state, and run() returns no
    actions and no fired entries for every one of the six events."""
    steps = []
    for event, data in SIX_EVENTS:
        steps.append({"run": [event, data]})
        steps.append({"actions": []})
        steps.append({"fired_ids": []})
        steps.append({"fired_count": 0})
    spec = {"cases": [
        {"name": "rules-missing",
         "pack": {"flags": {}, "claims": {}, "people": {}},
         "steps": steps},
        {"name": "rules-empty",
         "pack": {"rules": [], "flags": {}, "claims": {}, "people": {}},
         "steps": steps},
    ]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_comes_near_flag_off_says_once_and_leaves_the_flag_on(tmp_path: Path):
    """comes-near + if flag off + say fires, turns the flag on, and
    never fires again: `once` defaults to true. A second rule with no
    `if` proves the second event is blocked by `once` alone."""
    pack = {
        "flags": {"cat-noticed": "The cat has looked up at the hero once."},
        "claims": {},
        "people": {},
        "rules": [
            {"id": "cat-notices", "on": "cat",
             "when": {"comes-near": {"who": "cat", "distance": 2}},
             "if": [{"flag": "cat-noticed", "is": False}],
             "then": [{"set": "cat-noticed"},
                      {"say": {"who": "cat", "line": "Mrrp."}}]},
            {"id": "cat-wave", "on": "cat",
             "when": {"comes-near": {"who": "cat", "distance": 2}},
             "then": [{"say": "The cat watches."}]},
        ],
    }
    spec = {"cases": [{"name": "fires-once", "pack": pack, "steps": [
        {"run": ["comes-near", {"who": "cat", "distance": 1}]},
        {"fired_ids": ["cat-notices", "cat-wave"]},
        {"fired_count": 2},
        {"action_names": ["set", "say", "say"]},
        {"flag": ["cat-noticed", True]},
        {"why_contains": "cat-notices"},
        {"why_contains": "cat-wave"},
        {"run": ["comes-near", {"who": "cat", "distance": 1}]},
        {"actions": []},
        {"fired_ids": []},
        {"flag": ["cat-noticed", True]},
    ]}]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_once_false_fires_again_on_a_later_identical_event(tmp_path: Path):
    pack = {
        "flags": {}, "claims": {}, "people": {},
        "rules": [
            {"id": "greeter", "when": {"starts": {}}, "once": False,
             "then": [{"say": "Welcome back."}]},
        ],
    }
    spec = {"cases": [{"name": "once-false", "pack": pack, "steps": [
        {"run": ["starts", {}]},
        {"fired_ids": ["greeter"]},
        {"action_names": ["say"]},
        {"run": ["starts", {}]},
        {"fired_ids": ["greeter"]},
        {"action_names": ["say"]},
        {"run": ["starts", {}]},
        {"fired_ids": ["greeter"]},
    ]}]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_a_rule_that_does_not_match_leaves_state_untouched(tmp_path: Path):
    pack = {
        "flags": {"chest-opened": "The chest stands open."},
        "claims": {}, "people": {},
        "rules": [
            {"id": "chest-speaks", "on": "chest",
             "when": {"opens": {"what": "chest"}},
             "if": [{"flag": "chest-opened", "is": False}],
             "then": [{"set": "chest-opened"}, {"say": "Gold."}]},
        ],
    }
    spec = {"cases": [{"name": "no-match", "pack": pack, "steps": [
        {"snapshot": True},
        {"run": ["comes-near", {"who": "chest", "distance": 1}]},
        {"actions": []},
        {"fired_ids": []},
        {"state_unchanged": True},
        {"flag": ["chest-opened", False]},
    ]}]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_each_false_condition_blocks_the_rule(tmp_path: Path):
    """all-of, not, has and is-in - each false blocks; all true pass."""
    pack = {
        "flags": {"gate-open": "The gate stands open."},
        "claims": {}, "people": {"stern": {"believes": []}},
        "rules": [
            {"id": "r-flag", "when": {"comes-near": {"who": "stern", "distance": 2}},
             "once": False,
             "if": [{"flag": "gate-open", "is": True}],
             "then": [{"say": "The way is open."}]},
            {"id": "r-not", "when": {"comes-near": {"who": "stern", "distance": 2}},
             "once": False,
             "if": [{"not": {"flag": "gate-open", "is": False}}],
             "then": [{"say": "Not shut after all."}]},
            {"id": "r-has", "when": {"comes-near": {"who": "stern", "distance": 2}},
             "once": False,
             "if": [{"has": "cellar-key"}],
             "then": [{"say": "The key turns."}]},
            {"id": "r-is-in", "when": {"comes-near": {"who": "stern", "distance": 2}},
             "once": False,
             "if": [{"is-in": {"who": "stern", "place": "hall"}}],
             "then": [{"say": "Waiting in the hall."}]},
            {"id": "r-all-of", "when": {"comes-near": {"who": "stern", "distance": 2}},
             "once": False,
             "if": [{"all-of": [{"has": "cellar-key"},
                                {"flag": "gate-open", "is": True}]}],
             "then": [{"say": "Everything lines up."}]},
        ],
    }
    spec = {"cases": [{"name": "blocked", "pack": pack, "steps": [
        {"run": ["comes-near", {"who": "stern", "distance": 1}]},
        {"actions": []},
        {"fired_ids": []},
        {"fired_count": 0},
        # Make every condition true at once; each rule passes then.
        {"patch": {"flags": {"gate-open": True},
                   "items": {"cellar-key": True},
                   "where": {"stern": "hall"}}},
        {"run": ["comes-near", {"who": "stern", "distance": 1}]},
        {"fired_ids": ["r-flag", "r-not", "r-has", "r-is-in", "r-all-of"]},
        {"fired_count": 5},
    ]}]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_a_give_action_cannot_fire_a_picks_up_rule(tmp_path: Path):
    """No chains: the actions are returned to the caller and never
    fed back in as events, so a give does not become a picks-up."""
    pack = {
        "flags": {}, "claims": {}, "people": {},
        "rules": [
            {"id": "giver", "when": {"opens": {"what": "chest"}},
             "then": [{"give": "cellar-key"}]},
            {"id": "pickup-rule", "when": {"picks-up": {"what": "cellar-key"}},
             "if": [{"has": "cellar-key"}],
             "then": [{"say": "Taken."}]},
        ],
    }
    spec = {"cases": [{"name": "no-chains", "pack": pack, "steps": [
        {"run": ["opens", {"what": "chest"}]},
        {"fired_ids": ["giver"]},
        {"action_names": ["give"]},
        {"items": [["cellar-key", True]]},
        # Only a real picks-up event may fire the picks-up rule.
        {"run": ["picks-up", {"what": "cellar-key"}]},
        {"fired_ids": ["pickup-rule"]},
    ]}]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_beliefs_start_from_the_file_and_move_only_by_actions(tmp_path: Path):
    """A pack-declared belief starts true with its file as source;
    tells records the teller's id, believes records that the person
    saw it themselves, stops-believing clears it, and both
    not-believes and believes read the cleared value."""
    pack = {
        "flags": {},
        "claims": {
            "hero-took-key": {"meaning": "The hero took the cellar key.",
                              "true": False},
            "cellar-dark": {"meaning": "The cellar is dark.", "true": True},
        },
        "people": {"stern": {"believes": ["hero-took-key"]},
                   "fisher": {"believes": []}},
        "rules": [
            {"id": "passes-it-on", "when": {"enters": {"place": "hall"}},
             "once": False,
             "then": [{"tells": {"who": "fisher", "claim": "cellar-dark",
                                 "to": "stern"}}]},
            {"id": "sees-it", "when": {"opens": {"what": "chest"}},
             "once": False,
             "then": [{"believes": {"who": "fisher",
                                    "claim": "hero-took-key"}}]},
            {"id": "drops-it", "when": {"picks-up": {"what": "lamp"}},
             "once": False,
             "then": [{"stops-believing": {"who": "stern",
                                           "claim": "hero-took-key"}}]},
            {"id": "still-thinks",
             "when": {"comes-near": {"who": "stern", "distance": 2}},
             "once": False,
             "if": [{"believes": {"who": "stern", "claim": "hero-took-key"}}],
             "then": [{"say": "Stern glares."}]},
            {"id": "doubts-it",
             "when": {"comes-near": {"who": "stern", "distance": 2}},
             "once": False,
             "if": [{"not-believes": {"who": "stern",
                                      "claim": "hero-took-key"}}],
             "then": [{"say": "Stern shrugs."}]},
        ],
    }
    spec = {"cases": [{"name": "beliefs", "pack": pack, "steps": [
        # The author's mistaken assumption is believed from the start.
        {"belief": ["stern", "hero-took-key", True,
                    "written in the game file"]},
        {"run": ["comes-near", {"who": "stern", "distance": 1}]},
        {"fired_ids": ["still-thinks"]},
        {"run": ["enters", {"place": "hall"}]},
        {"belief": ["stern", "cellar-dark", True, "told by fisher"]},
        {"run": ["opens", {"what": "chest"}]},
        {"belief": ["fisher", "hero-took-key", True, "saw it themselves"]},
        {"run": ["picks-up", {"what": "lamp"}]},
        {"belief": ["stern", "hero-took-key", False, "stopped believing"]},
        # A belief that is false blocks `believes`; `not-believes`
        # reads the cleared value.
        {"run": ["comes-near", {"who": "stern", "distance": 1}]},
        {"fired_ids": ["doubts-it"]},
        {"why_contains": "doubts-it"},
    ]}]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_every_action_name_round_trips_unchanged(tmp_path: Path):
    """Every action name reaches the caller's actions array as the
    rule's own object, so the later wiring never has to translate."""
    pack = {
        "flags": {"gate-open": "The gate stands open."},
        "claims": {}, "people": {"stern": {"believes": []}},
        "rules": [
            {"id": "all-actions", "when": {"starts": {}},
             "then": [
                 {"say": "The wind turns."},
                 {"say": {"who": "stern", "line": "You again."}},
                 {"show": "cellar-panel"},
                 {"hide": "carpet"},
                 {"reveal": "chest-monster"},
                 {"give": "lamp"},
                 {"set": "gate-open"},
                 {"unset": "gate-open"},
                 {"believes": {"who": "stern", "claim": "hero-took-key"}},
                 {"stops-believing": {"who": "stern",
                                      "claim": "hero-took-key"}},
                 {"tells": {"who": "stern", "claim": "hero-took-key",
                            "to": "fisher"}},
                 {"weather": "fog"},
                 {"point-to": "harbour"},
             ]},
        ],
    }
    spec = {"cases": [{"name": "round-trip", "pack": pack, "steps": [
        {"run": ["starts", {}]},
        {"fired_ids": ["all-actions"]},
        {"action_names": ["say", "say", "show", "hide", "reveal", "give",
                          "set", "unset", "believes", "stops-believing",
                          "tells", "weather", "point-to"]},
        {"same_objects": "all-actions"},
    ]}]}
    assert "all checks passed" in _run(tmp_path, spec)


def test_the_why_sentence_is_one_string_containing_the_rule_id(tmp_path: Path):
    """One plain sentence per fired rule, rule id first - the same
    line a later task writes to the journal."""
    pack = {
        "flags": {}, "claims": {}, "people": {},
        "rules": [
            {"id": "harbour-fog", "when": {"enters": {"place": "harbour"}},
             "then": [{"weather": "fog"}]},
            {"id": "key-opens-panel",
             "when": {"uses-with": {"item": "cellar-key", "with": "panel"}},
             "if": [{"has": "cellar-key"}],
             "then": [{"reveal": "panel"}, {"set": "gate-open"}]},
        ],
    }
    spec = {"cases": [{"name": "why", "pack": pack, "steps": [
        {"run": ["enters", {"place": "harbour"}]},
        {"fired_count": 1},
        {"why_contains": "harbour-fog"},
        {"patch": {"items": {"cellar-key": True}}},
        {"items": [["cellar-key", True]]},
        {"run": ["uses-with", {"item": "cellar-key", "with": "panel"}]},
        {"fired_count": 1},
        {"why_contains": "key-opens-panel"},
    ]}]}
    out = _run(tmp_path, spec)
    assert "all checks passed" in out
