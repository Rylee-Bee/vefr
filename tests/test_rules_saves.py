"""Durable rule saves (docs/plans/durable-rule-saves-plan.md): S1-S8, S10, S12, S15-S17.

FROZEN CONTRACT. A pack's `saves` block picks what a reload keeps:
  "saves": {"rules": "persist" | "reset", "legacy": "fresh" | "from-log"}
Absent block or absent `rules` means reset = today's behavior (those tests pass now and pin it).
Persist behavior landed with the player work (plan PR 2); the one strict xfail left is the
pre-existing localStorage-throws gap (issue #224). Plays the REAL woven file in jsdom, one session at a
time; a reload is the previous session's printed `store` fed into the next session.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_rules_pack as mk  # noqa: E402

HARNESS = ROOT / "tests" / "fixtures" / "rules_save_harness.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

PERSIST = {"rules": "persist"}
WORLD = "rules-saves-a"
RULESTATE = f"vefr-rulestate-{WORLD}"
WHYKEY = f"vefr-rules-{WORLD}"


def weave(tmp_path, saves=None, name=WORLD, variant="a", sub="p"):
    pack = mk.build_saves(tmp_path / sub, saves=saves, name=name, variant=variant)
    out = tmp_path / sub / f"{name}-{variant}.html"
    out.write_text(cli.weave_html(pack), encoding="utf-8")
    return out


def session(html, store=None, walk=("right",), begin=True, storage="ok", peek=False):
    spec = {"store": store or {}, "walk": list(walk), "begin": begin, "storage": storage, "peek": peek}
    run = subprocess.run(["node", str(HARNESS), str(html), json.dumps(spec)],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def ids(result):
    return [e["id"] for e in result["why"]]


# --- reset and absent: today's behavior, pinned (these pass now) -----------------------------

@pytest.mark.parametrize("saves", [None, {"rules": "reset"}, {}], ids=["absent", "reset", "empty-block"])
def test_s5_reset_replays_once_rules_and_never_writes_a_rule_state_key(tmp_path, saves):
    html = weave(tmp_path, saves)
    first = session(html)
    second = session(html, store=first["store"])
    assert ids(first).count("the-game-awakens") == 1
    assert ids(second).count("the-game-awakens") == 2          # the once rule fired again
    assert not any(k.startswith("vefr-rulestate-") for k in first["store"] | second["store"])
    assert first["errors"] == [] and second["errors"] == []


def test_s9_start_over_removes_the_rule_state_key():
    """`startoverKeys` removes every vefr- key, so the new key is cleared with the rest."""
    src = (ROOT / "web" / "packaged.html").read_text(encoding="utf-8")
    block = src.split("// -- startover start --", 1)[1].split("// -- startover end --", 1)[0]
    assert "'vefr-'" in block or '"vefr-"' in block


# --- persist -------------------------------------------------------------------------------

def test_s1_a_fired_once_rule_does_not_fire_again_and_the_why_log_is_not_doubled(tmp_path):
    html = weave(tmp_path, PERSIST)
    first = session(html)
    second = session(html, store=first["store"])
    assert ids(second).count("the-game-awakens") == 1
    assert second["state"]["fired"]["the-game-awakens"] is True
    assert RULESTATE in second["store"]


def test_s2_a_set_flag_survives_a_reload_with_no_event_fired(tmp_path):
    html = weave(tmp_path, PERSIST)
    first = session(html)
    assert first["state"]["flags"].get("lit") is True
    loaded = session(html, store=first["store"], walk=(), peek=True)
    assert loaded["state"]["flags"].get("lit") is True              # read from the save, not re-set by a rule
    assert ids(loaded) == ids(first)                                # and nothing fired to put it there


def test_s3_a_repeating_rule_still_fires_after_reload(tmp_path):
    html = weave(tmp_path, PERSIST)
    first = session(html)
    second = session(html, store=first["store"])
    assert ids(first).count("keeper-again") == 1
    assert ids(second).count("keeper-again") == 2


def test_s4_all_four_parts_survive_and_deep_equal(tmp_path):
    html = weave(tmp_path, PERSIST)
    first = session(html)
    second = session(html, store=first["store"], walk=(), peek=True)
    a, b = first["state"], second["state"]
    assert a["items"].get("torch") and a["items"].get("chalked-map")
    assert a["beliefs"]["fisher"]["keeper-guards-gate"]["source"]
    assert {"the-game-awakens", "gossip", "gift", "keeper-is-near"} <= set(a["fired"])
    for part in ("flags", "fired", "beliefs", "items"):
        assert b[part] == a[part], part


def test_s6_a_changed_pack_recovers_and_keeps_what_it_still_knows(tmp_path):
    a_html = weave(tmp_path, PERSIST, variant="a", sub="a")
    first = session(a_html)
    assert "saw" in first["state"]["flags"] and "gift2" in first["state"]["fired"]
    b_html = weave(tmp_path, PERSIST, variant="b", sub="b")
    second = session(b_html, store=first["store"], walk=(), peek=True)
    state = second["state"]
    assert second["errors"] == []
    assert "saw" not in state["flags"]                              # flag removed from the pack
    assert "gift2" not in state["fired"] and "learn" not in state["fired"]
    assert "extra-claim" not in state["beliefs"].get("fisher", {})  # claim removed
    assert "chalked-map" not in state["items"]                      # item removed
    assert state["flags"].get("lit") is True and state["items"].get("torch")  # kept ids keep values
    assert "gossip" in state["fired"]
    walked = session(b_html, store=first["store"])
    assert "newcomer" in ids(walked)                                 # the new rule can fire


@pytest.mark.parametrize("bad", ["not json at all", "[]", "{\"v\": 0}", "{\"v\": 1, \"flags\": \"x\", \"fired\": 5}"])
def test_s7_unreadable_data_gives_a_fresh_state_and_no_error(tmp_path, bad):
    html = weave(tmp_path, PERSIST)
    result = session(html, store={RULESTATE: bad})
    assert result["errors"] == []
    assert ids(result).count("the-game-awakens") == 1               # fresh state: the rule fired
    assert result["state"]["flags"].get("lit") is True
    saved = json.loads(result["store"][RULESTATE])                  # rewritten as a valid save
    assert saved["v"] == 1 and isinstance(saved["flags"], dict) and isinstance(saved["fired"], dict)


def test_s7_a_newer_save_is_left_untouched(tmp_path):
    html = weave(tmp_path, PERSIST)
    newer = json.dumps({"v": 2, "flags": {"lit": True}, "future": "kept"})
    result = session(html, store={RULESTATE: newer})
    assert result["errors"] == []
    assert result["store"][RULESTATE] == newer


@pytest.mark.parametrize("storage", [
    pytest.param("get-throws", marks=pytest.mark.xfail(
        strict=True, reason="PRE-EXISTING: the player reads window.localStorage unguarded somewhere "
                            "(a sandboxed iframe throws); today Begin dies and `starts` never fires. "
                            "Own fix, outside rule saves.")),
    "set-throws"])
def test_s8_unavailable_storage_never_stops_the_game(tmp_path, storage):
    html = weave(tmp_path, PERSIST)
    result = session(html, storage=storage)
    assert result["errors"] == []
    assert ids(result).count("the-game-awakens") == 1               # rules ran in memory
    assert result["state"]["flags"].get("lit") is True


def test_s10_two_worlds_keep_separate_state(tmp_path):
    a = weave(tmp_path, PERSIST, name="rules-saves-a", sub="a")
    b = weave(tmp_path, PERSIST, name="rules-saves-b", sub="b")
    first = session(a)
    second = session(b, store=first["store"])
    assert ids(second).count("the-game-awakens") == 1               # world b did not see world a's save
    assert "vefr-rulestate-rules-saves-a" in second["store"]
    assert "vefr-rulestate-rules-saves-b" in second["store"]


def test_s17_starts_fires_once_per_save_and_again_after_start_over(tmp_path):
    html = weave(tmp_path, PERSIST)
    first = session(html)
    second = session(html, store=first["store"])
    assert ids(first).count("hello") == 1
    assert ids(second).count("hello") == 1                          # not replayed on reload
    cleared = {k: v for k, v in second["store"].items() if not k.startswith("vefr-")}
    third = session(html, store=cleared)                            # what Start over leaves
    assert ids(third).count("hello") == 1


def test_s17_in_reset_mode_starts_still_fires_on_every_load(tmp_path):
    html = weave(tmp_path, {"rules": "reset"})
    first = session(html)
    second = session(html, store=first["store"])
    assert ids(second).count("hello") == 2


# --- old saves: saves.legacy ---------------------------------------------------------------

LOG_ONLY = {WHYKEY: json.dumps([
    {"id": "the-game-awakens", "why": "rule 'the-game-awakens' fired: the game began."},
    {"id": "ghost-rule", "why": "rule 'ghost-rule' fired: no such rule any more."}])}


def test_s15_from_log_marks_exactly_the_rules_the_log_proves_fired(tmp_path):
    html = weave(tmp_path, {"rules": "persist", "legacy": "from-log"})
    result = session(html, store=LOG_ONLY, walk=())
    assert result["errors"] == []
    walked = session(html, store=LOG_ONLY, walk=("right",))
    assert walked["state"]["fired"].get("the-game-awakens") is True
    assert "ghost-rule" not in walked["state"]["fired"]             # unknown id is ignored
    assert "keeper-is-near" in ids(walked)                          # not in the log: still fires
    assert [i for i in ids(walked) if i == "the-game-awakens"] == ["the-game-awakens"]  # only the logged one


def test_s16_fresh_legacy_marks_nothing_from_the_log(tmp_path):
    html = weave(tmp_path, {"rules": "persist", "legacy": "fresh"})
    result = session(html, store=LOG_ONLY)
    assert ids(result).count("the-game-awakens") == 2               # fired again: once, as promised


def test_s16_legacy_defaults_to_fresh(tmp_path):
    html = weave(tmp_path, PERSIST)
    result = session(html, store=LOG_ONLY)
    assert ids(result).count("the-game-awakens") == 2


# --- bake -----------------------------------------------------------------------------------

@pytest.mark.parametrize("saves", [None, {"rules": "persist", "legacy": "from-log"}], ids=["absent", "declared"])
def test_s12_the_bake_carries_saves_only_when_declared(tmp_path, saves):
    world = session(weave(tmp_path, saves), walk=())["world"]
    if saves is None:
        assert "saves" not in world
    else:
        assert world["saves"] == saves
