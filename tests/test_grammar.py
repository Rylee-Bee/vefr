"""Pack grammars: the seeded expander, the pack wiring, the validator.

A grammar is data an author writes in `world.json`; the engine expands
it with no model and no pool (see src/vefr/grammar.py). These tests
pin the four promises the contract makes - the same seed gives the
same line, references resolve, expansion stops at a cap, and a pack
with a broken grammar hears about it from `norns validate` rather
than from a silent whisper - plus the two places the engine reads a
grammar: the woven player (baked into the file) and `norns delve`
(floor names).
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from vefr import cli, grammar, maplab

# The worked example from the pack contract (world.py) and the guide.
WHISPER = {
    "origin": ["#who# says #news#."],
    "who": ["the innkeeper", "the ferryman"],
    "news": ["the road east is watched", "the ford is out"],
}
WEATHER = {
    "origin": ["#sky# over #place#."],
    "sky": ["Rain", "Hard frost"],
    "place": ["the town", "the ridge"],
}
NAMES = {
    "origin": ["#adj# #noun#"],
    "adj": ["Grey", "Still"],
    "noun": ["Hollow", "Reach"],
}

ALL = {"whisper": WHISPER, "weather": WEATHER, "name": NAMES}


# ------------------------------------------------------- the expander itself

def test_the_same_seed_gives_the_same_line():
    first = grammar.expand(ALL["weather"], random.Random("dusk"))
    second = grammar.expand(ALL["weather"], random.Random("dusk"))
    assert first == second
    assert first in {"Rain over the town.", "Rain over the ridge.",
                     "Hard frost over the town.", "Hard frost over the ridge."}


def test_expand_seeded_is_the_seeded_expand():
    assert (grammar.expand_seeded(ALL["name"], "floor-2")
            == grammar.expand(ALL["name"], random.Random("floor-2")))


def test_different_seeds_can_say_different_things():
    drawn = {grammar.expand_seeded(ALL["weather"], f"seed-{i}") for i in range(50)}
    assert len(drawn) > 1, "the rng never varied the line"


def test_references_resolve_and_literal_text_is_kept():
    line = grammar.expand(ALL["whisper"], random.Random(1))
    assert line.startswith(("the innkeeper says", "the ferryman says"))
    assert line.endswith(".")
    # The whole grammar draws only words it was given: every token,
    # punctuation aside, is a word some rule of the pack declares.
    declared = {w for rule in ALL["whisper"].values() for entry in rule
                for w in re.findall(r"[a-z]+", entry)}
    assert set(re.findall(r"[a-z]+", line)) <= declared


def test_references_nest():
    grammar_ = {
        "origin": ["#outer#!"],
        "outer": ["#inner# and #inner#"],
        "inner": ["deep"],
    }
    assert grammar.expand(grammar_, random.Random(3)) == "deep and deep!"


def test_a_reference_to_a_missing_rule_expands_to_nothing():
    """Not half a line: the honest empty string, never a hole."""
    assert grammar.expand({"origin": ["the #missing# end."]},
                          random.Random(1)) == ""


def test_a_grammar_without_origin_expands_to_nothing():
    assert grammar.expand({"who": ["the innkeeper"]}, random.Random(1)) == ""


def test_a_non_mapping_grammar_expands_to_nothing():
    assert grammar.expand(["#origin#"], random.Random(1)) == ""
    assert grammar.expand(None, random.Random(1)) == ""


def test_an_empty_or_malformed_rule_expands_to_nothing():
    assert grammar.expand({"origin": []}, random.Random(1)) == ""
    assert grammar.expand({"origin": "not a list"}, random.Random(1)) == ""
    assert grammar.expand({"origin": [42]}, random.Random(1)) == ""


def test_a_grammar_that_feeds_itself_stops_at_the_cap():
    """The cap is the whole point: a loop stops, it does not hang."""
    assert grammar.expand({"origin": ["#origin# again"]},
                          random.Random(1)) == ""
    # Two rules pointing at each other trip it just the same.
    assert grammar.expand(
        {"origin": ["#a#"], "a": ["#b#"], "b": ["#a#"]},
        random.Random(1)) == ""


def test_the_cap_is_a_number_the_caller_can_move():
    text = "#a# #a# #a#"
    three = {"origin": [text], "a": ["x"]}
    assert grammar.expand(three, random.Random(1), limit=10) == "x x x"
    # Two draws only: the third reference finds the budget spent.
    assert grammar.expand(three, random.Random(1), limit=2) == ""


def test_the_default_cap_is_the_documented_two_hundred():
    assert grammar.MAX_EXPANSIONS == 200
    # The cap counts the origin draw too, so a grammar whose origin
    # names 199 rules is the last that fits and 200 is the first that
    # does not.
    def needs(n: int) -> dict:
        return {"origin": [" ".join(["#a#"] * n)], "a": ["x"]}

    assert grammar.expand(needs(grammar.MAX_EXPANSIONS - 1), random.Random(1))
    assert grammar.expand(needs(grammar.MAX_EXPANSIONS), random.Random(1)) == ""


# ------------------------------------------------------------- the validator

def test_a_good_grammar_block_passes():
    assert maplab.grammar_errors(ALL) == []
    assert maplab.grammar_errors({}) == []


def test_a_grammar_without_origin_is_rejected():
    errors = maplab.grammar_errors({"whisper": {"who": ["the innkeeper"]}})
    assert len(errors) == 1
    assert "whisper" in errors[0] and "origin" in errors[0]


def test_an_unknown_reference_is_rejected():
    errors = maplab.grammar_errors(
        {"whisper": {"origin": ["#townsfolk# murmur"]}})
    assert len(errors) == 1
    assert "townsfolk" in errors[0] and "not a rule" in errors[0]


def test_an_empty_rule_is_rejected():
    errors = maplab.grammar_errors({"name": {"origin": [], "adj": ["Grey"]}})
    assert len(errors) == 1
    assert "'origin'" in errors[0] and "non-empty list of strings" in errors[0]


def test_a_rule_of_the_wrong_shape_is_rejected():
    for bad in ("a string", 42, {"a": 1}, [1, 2]):
        errors = maplab.grammar_errors({"name": {"origin": ["x"],
                                                 "adj": bad}})
        assert errors, f"accepted a rule shaped {bad!r}"


def test_a_grammar_that_is_not_an_object_is_rejected():
    assert maplab.grammar_errors(["whisper"])
    assert maplab.grammar_errors({"whisper": "not a grammar"})


def test_validate_reports_a_broken_grammar(tmp_path):
    """End to end through the real pack shape, as `norns validate` runs it."""
    pack = _pack_with(tmp_path, "broken", grammars={"whisper": {"origin": ["#nope#"]}})
    errors = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    assert any("nope" in e for e in errors), errors

    good = _pack_with(tmp_path, "good", grammars=ALL)
    assert maplab.validate(maplab.load_pack(good), pack_dir=good) == []


def test_a_pack_with_no_grammars_validates_exactly_as_before(tmp_path):
    """The block is additive: absent means the pack behaves as it always has."""
    pack = _pack_with(tmp_path, "plain")
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == []
    assert maplab.load_pack(pack).get("grammars", {}) == {}


# -------------------------------------------------------------- the wiring

def test_the_grammar_block_is_carried_by_the_loader(tmp_path):
    from vefr.world import load_world

    pack = _pack_with(tmp_path, "carried", grammars=ALL)
    assert load_world(str(pack))["grammars"] == ALL


def test_the_grammar_block_is_baked_into_the_woven_player(tmp_path):
    html = cli.weave_html(_pack_with(tmp_path, "baked", grammars=ALL))
    assert "{{grammars_json}}" not in html
    baked = re.search(r"window\.VEFR_GRAMMARS = (.*?);\n", html)
    assert baked, "the woven file carries no grammar block"
    assert json.loads(baked.group(1)) == ALL


def test_a_pack_with_no_grammars_bakes_an_empty_block(tmp_path):
    html = cli.weave_html(_pack_with(tmp_path, "silent"))
    assert re.search(r"window\.VEFR_GRAMMARS = \{\};\n", html)


def test_the_woven_player_speaks_a_grammar_offline(tmp_path):
    """The shipped file keeps its voice with no model, no pool, no bank."""
    html = cli.weave_html(_pack_with(tmp_path, "offline", grammars=ALL))
    # The whisper fallback is wired in after the fragment banks and
    # before the honest silence.
    assert "whisperFromGrammar()" in html
    assert html.index("whisperFromFragments()") < html.index("whisperFromGrammar()")
    assert html.index("whisperFromGrammar()") < html.index("Nothing came back (")
    assert "From the world's own words." in html
    # Weather: on arrival, in the status line, journaled, never per step.
    assert "sayArrivalWeather(name);" in html
    assert "grammarFromPack('weather')" in html
    assert "journalVisit(name, hero[0], hero[1]);" in html


def test_delve_names_a_floor_from_the_name_grammar(tmp_path, capsys):
    pack = _pack_with(tmp_path, "named", grammars=ALL)
    assert cli.cmd_delve(_delve_args(pack)) == 0
    contract = json.loads(
        (pack / "acts" / "act-1" / "floor-2" / "contract.json")
        .read_text(encoding="utf-8"))
    drawn = grammar.expand_seeded(NAMES, "cavern:floor-2:name")
    assert contract["name"] == drawn
    assert contract["title"] == drawn
    # The geometry is untouched, and the directory keeps its floor-N
    # name, so paths and doors are exactly what they always were.
    assert contract["hero_start"] and contract["legend"]
    assert (pack / "acts" / "act-1" / "floor-2" / "map.md").exists()
    assert f'named "{drawn}"' in capsys.readouterr().out


def test_delve_without_a_name_grammar_names_nothing(tmp_path):
    """Today's naming, exactly: no `name` and no `title` in the contract."""
    pack = _pack_with(tmp_path, "unnamed")
    assert cli.cmd_delve(_delve_args(pack)) == 0
    contract = json.loads(
        (pack / "acts" / "act-1" / "floor-2" / "contract.json")
        .read_text(encoding="utf-8"))
    assert "name" not in contract and "title" not in contract


def test_delve_naming_is_seeded_not_drawn(tmp_path):
    """The same seed names the same floor, every time it is asked."""
    first = _pack_with(tmp_path, "same-a", grammars=ALL)
    second = _pack_with(tmp_path, "same-b", grammars=ALL)
    assert cli.cmd_delve(_delve_args(first)) == 0
    assert cli.cmd_delve(_delve_args(second)) == 0
    read = lambda p: json.loads(               # noqa: E731 - a one-line read
        (p / "acts" / "act-1" / "floor-2" / "contract.json")
        .read_text(encoding="utf-8"))["name"]
    assert read(first) == read(second)


def test_a_broken_name_grammar_fails_the_run_and_leaves_no_floor(tmp_path, capsys):
    """A grammar that refuses writes no name at all, never half a one, and
    the run fails so the author hears about it from the tool. Since
    vefr#336 a failed bake leaves the pack exactly as it was, so the
    floor it was building is not left behind, named or unnamed."""
    pack = _pack_with(tmp_path, "broken-name",
                      grammars={"name": {"origin": ["#missing#"]}})
    assert cli.cmd_delve(_delve_args(pack)) != 0
    assert "missing" in capsys.readouterr().out
    assert not (pack / "acts" / "act-1" / "floor-2").exists()


# ------------------------------------------------------------------ helpers

def _pack_with(root: Path, name: str, grammars=None) -> Path:
    """A minimal acts pack with one town and one walkable down-stair.

    The same shape tests/test_delve.py builds, so `norns delve` can
    generate a floor under it.
    """
    pack = root / "worlds" / name
    act = pack / "acts" / "act-1"
    (act / "town").mkdir(parents=True)
    config = {
        "title": "Grammar Test",
        "phases": {"dusk": "quiet", "dawn": "warm"},
        "voices": {},
    }
    if grammars is not None:
        config["grammars"] = grammars
    (pack / "world.json").write_text(json.dumps(config), encoding="utf-8")
    (act / "world.json").write_text(json.dumps({
        "id": "act-1",
        "title": "Grammar Test",
        "regions": ["town"],
        "speakers": {},
        "transitions": [],
    }), encoding="utf-8")
    (act / "town" / "map.md").write_text(
        "#########\n#.......#\n#.......#\n#...d...#\n#.......#\n"
        "#.......#\n#########\n", encoding="utf-8")
    (act / "town" / "contract.json").write_text(json.dumps({
        "tile": 32,
        "bg": "#131311",
        "hero_start": [1, 1],
        "legend": {
            ".": {"base": ["#212a20"], "tile": "dungeon-floor"},
            "#": {"base": ["#2a2e33"], "solid": True, "tile": "dungeon-wall"},
            "d": {"base": ["#2b2f38"], "tile": "dungeon-stairs-down"},
        },
        "sanctuary_tiles": ["."],
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [],
        "pois": {},
    }), encoding="utf-8")
    return pack


def _delve_args(pack: Path) -> argparse.Namespace:
    return argparse.Namespace(
        pack=str(pack), seed="cavern", floors=1,
        from_region="town", from_at="4,3",
        width=30, height=20, rooms=8,
        first_name=None, force=False,
    )
