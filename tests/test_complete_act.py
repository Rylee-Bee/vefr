"""The `complete-act` rule action (Cottage release 1, plan V1). FROZEN CONTRACT.

A pack can end a story beat with one rule action: {"complete-act": "<act id>"}.
  - validator: the value must be a string naming an act the pack declares; anything else is one plain
    sentence naming the rule (and, for an unknown act, the act id).
  - engine: the pure rules engine accepts the action (a rule using it is not skipped as malformed).
  - player: it opens an end card on the overlay surface: element #act-end, role=dialog, aria-modal,
    labelled by a heading, with the buttons "Keep exploring" and "Start over"; focus lands on
    "Keep exploring". Interact (E) continues = closes the card. It does NOT advance acts.
    window.VEFR_ACT_COMPLETE = {act, shown} is the harness snapshot.
  - once per save: with saves.rules=persist a reload does not show the card again.
  - a pack that never uses the action plays exactly as before (no #act-end element at all).
Neutral fixtures only: VEFR is public.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_lock_pack as mk  # noqa: E402

HARNESS = ROOT / "tests" / "fixtures" / "act_end_harness.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

END_RULE = {"id": "the-end", "when": {"starts": {}}, "once": True,
            "then": [{"complete-act": "act-1"}]}


def build(tmp_path, rules=None, persist=False):
    pack = mk.build(tmp_path)
    cfg_path = pack / "world.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["flags"], cfg["claims"], cfg["people"] = {}, {}, {}
    cfg["rules"] = rules if rules is not None else []
    if persist:
        cfg["saves"] = {"rules": "persist", "legacy": "fresh"}
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    return pack


def extra_errors(tmp_path, rules):
    bpack = build(tmp_path / "b")
    base = maplab.validate(maplab.load_pack(bpack), pack_dir=bpack)
    pack = build(tmp_path / "x", rules)
    got = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    return [e for e in got if e not in base]


def rule(value):
    return {"id": "the-end", "when": {"starts": {}}, "then": [{"complete-act": value}]}


# --- validator -------------------------------------------------------------------------------

def test_a_declared_act_is_accepted(tmp_path):
    assert extra_errors(tmp_path, [rule("act-1")]) == []


def test_an_unknown_act_is_named(tmp_path):
    errs = extra_errors(tmp_path, [rule("act-9")])
    assert any("the-end" in e and "act-9" in e for e in errs), errs


@pytest.mark.parametrize("bad", [7, True, None, {"act": "act-1"}, ["act-1"]])
def test_a_non_string_value_is_refused(tmp_path, bad):
    errs = extra_errors(tmp_path, [rule(bad)])
    assert any("the-end" in e and "complete-act" in e for e in errs), errs


# --- engine and player -------------------------------------------------------------------------

def play(tmp_path, spec, rules, persist=False):
    pack = build(tmp_path, rules, persist)
    html = tmp_path / "end.html"
    html.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), json.dumps(spec)],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_the_end_card_opens_accessibly(tmp_path):
    r = play(tmp_path, {}, [END_RULE])
    assert r["errors"] == []
    assert r["complete"] == {"act": "act-1", "shown": True}
    c = r["card"]
    assert c["present"] and c["visible"]
    assert c["role"] == "dialog" and c["modal"] == "true" and c["labelled"]
    assert "Keep exploring" in c["buttons"] and "Start over" in c["buttons"]
    assert c["focusLabel"] == "Keep exploring"


def test_interact_closes_the_card_and_does_not_advance(tmp_path):
    r = play(tmp_path, {"press": "e"}, [END_RULE])
    assert r["card"]["visible"] is True
    assert not (r["after"]["present"] and r["after"]["visible"])
    assert r["errors"] == []


def test_once_per_save_survives_a_reload(tmp_path):
    first = play(tmp_path / "one", {}, [END_RULE], persist=True)
    assert first["card"]["visible"] is True
    second = play(tmp_path / "two", {"store": first["store"]}, [END_RULE], persist=True)
    assert not (second["card"]["present"] and second["card"]["visible"])
    assert second["complete"] is None


def test_a_pack_without_the_action_has_no_card(tmp_path):
    r = play(tmp_path, {}, [])
    assert r["card"]["present"] is False
    assert r["complete"] is None
    assert r["errors"] == []
