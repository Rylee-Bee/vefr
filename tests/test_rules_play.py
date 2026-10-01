"""The rules wiring, played: the REAL woven file, driven in jsdom.

The harness (tests/fixtures/rules_play_harness.mjs, in the style of
combat_harness.mjs) weaves the fixture pack (make_rules_pack.py: sample
world + one flag, one claim, one person, two rules), presses Begin so
the `starts` rule fires, then takes one step right onto a named place
so the `comes-near` rule fires. Asserted here: each event fired its own
rule, the player's rule log holds one plain sentence per fired rule
(each naming its rule id), the engine state carries the flag and the
belief's source, and the log is persisted under the file's per-world
localStorage pattern.

Deterministic: the fixture is fixed, so every string is pinned.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "rules_play_harness.mjs"
MAKE = ROOT / "tests" / "fixtures" / "make_rules_pack.py"


@pytest.fixture(scope="module")
def play(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("rules-home")
    made = subprocess.run(
        [sys.executable, str(MAKE), str(home)],
        capture_output=True, text=True, timeout=120)
    assert made.returncode == 0, made.stderr
    pack = Path(made.stdout.strip())
    out = home / "rules.html"
    out.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(
        ["node", str(HARNESS), str(out)],
        capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_the_start_rule_fires_when_begin_is_pressed(play):
    start = play["afterStart"]
    assert [e["id"] for e in start] == ["the-game-awakens"]
    assert start[0]["why"] == "rule 'the-game-awakens' fired: the game began."
    # The narrator line the say action wrote through the combat log.
    assert play["narratorAfterStart"] == "The rules are awake."


def test_the_walk_fires_the_comes_near_rule(play):
    walked = play["afterWalk"]
    assert [e["id"] for e in walked] == ["the-game-awakens",
                                         "keeper-is-near"]
    assert walked[1]["why"] == "rule 'keeper-is-near' fired: the hero came near keeper."
    assert play["poi"] == "keeper"
    assert play["narrator"] == "Someone waits by the path."


def test_the_rule_log_holds_one_plain_sentence_per_fired_rule(play):
    entries = play["afterWalk"]
    assert len(entries) == 2
    for entry in entries:
        assert set(entry) == {"id", "why"}
        # one plain sentence, rule id first, ending in a full stop
        assert entry["why"].startswith(f"rule '{entry['id']}' fired:")
        assert entry["why"].endswith(".")
        assert "\n" not in entry["why"]


def test_the_engine_state_carries_the_flag_and_the_belief_source(play):
    assert play["flags"] == {"lit": True}
    assert play["beliefs"]["keeper"]["keeper-guards-gate"] == {
        "value": True, "source": "written in the game file"}


def test_the_rule_log_is_persisted_per_world(play):
    stored = json.loads(play["stored"])
    assert [e["id"] for e in stored] == ["the-game-awakens", "keeper-is-near"]
    assert len(stored) <= 20
