"""The validator for the optional flags/claims/people/rules catalog.

A pack that declares none of the four keys must validate exactly as
before - worlds/sample-world proves that below. A pack that declares
any of them gets every rule, condition, action and id checked by
`maplab.rules_errors`, surfaced through `maplab.validate`, as plain
sentences that name the rule id.

`maplab.rules_notes` is the two-warning sibling: deliberately NOT
wired into validate(), so its cases assert both the note and the
clean validate pass.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from vefr import maplab

SAMPLE = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"

FLAGS = {"lit": "the torch is burning", "met-keeper": "the keeper has been greeted"}
CLAIMS = {"keeper-guards-gate": {"meaning": "the keeper guards the gate",
                                 "true": True}}
PEOPLE = {"keeper": {"believes": ["keeper-guards-gate"]}}


def _copy_sample(tmp_path: Path) -> Path:
    pack = tmp_path / "sample-world"
    shutil.copytree(SAMPLE, pack)
    return pack


def _pack(tmp_path: Path, additions: dict) -> Path:
    """The sample pack with `additions` merged into its pack-level world.json."""
    pack = _copy_sample(tmp_path)
    cfg = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    cfg.update(additions)
    (pack / "world.json").write_text(json.dumps(cfg), encoding="utf-8")
    return pack


def _errors(pack: Path) -> list[str]:
    return maplab.rules_errors(maplab.load_pack(pack), pack_dir=pack)


def _validate(pack: Path) -> list[str]:
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def _one(tmp_path: Path, rule: dict, **extra) -> list[str]:
    """Rules errors for a pack with one rule under test (plus extras)."""
    additions = {"flags": dict(FLAGS), "claims": dict(CLAIMS),
                 "people": dict(PEOPLE), "rules": [rule]}
    additions.update(extra)
    return _errors(_pack(tmp_path, additions))


# --- the GOOD pack: all six events, a spread of conditions/actions -------

GOOD_RULES = [
    {"id": "world-awakens", "when": {"starts": {}},
     "if": [{"flag": "lit", "is": False}],
     "then": [{"set": "lit"}, {"say": "The world draws breath."}],
     "once": True},
    {"id": "hero-enters-town", "when": {"enters": {"place": "town"}},
     "if": [{"has": "torch"}, {"is-in": {"who": "keeper", "place": "town"}}],
     "then": [{"give": "chalked-map"}, {"point-to": "town"},
              {"show": "keeper"}]},
    {"id": "keeper-comes-near", "when": {"comes-near": {"who": "keeper",
                                                        "distance": 2}},
     "if": [{"believes": {"who": "keeper", "claim": "keeper-guards-gate"}}],
     "then": [{"say": {"who": "keeper", "line": "The gate stays shut."}},
              {"set": "met-keeper"}]},
    {"id": "torch-opens-door", "on": "torch", "when": {"opens": {"what": "torch"}},
     "then": [{"reveal": "chalked-map"}, {"weather": "fog"}]},
    {"id": "map-picked-up", "when": {"picks-up": {"what": "chalked-map"}},
     "if": [{"not": {"flag": "lit", "is": True}},
            {"not-believes": {"who": "keeper",
                              "claim": "keeper-guards-gate"}}],
     "then": [{"hide": "chalked-map"}, {"unset": "lit"}]},
    {"id": "torch-on-map", "when": {"uses-with": {"item": "torch",
                                                  "with": "chalked-map"}},
     "if": [{"all-of": [{"has": "torch"},
                        {"is-in": {"who": "keeper", "place": "town"}}]}],
     "then": [{"believes": {"who": "keeper", "claim": "keeper-guards-gate"}},
              {"tells": {"who": "keeper", "claim": "keeper-guards-gate",
                         "to": "keeper"}},
              {"stops-believing": {"who": "keeper",
                                   "claim": "keeper-guards-gate"}},
              {"weather": "clear"}]},
]


def test_a_good_pack_with_all_six_events_gets_no_rule_errors(tmp_path):
    pack = _pack(tmp_path, {"flags": FLAGS, "claims": CLAIMS, "people": PEOPLE,
                            "rules": GOOD_RULES})
    errors = _validate(pack)
    ids = [rule["id"] for rule in GOOD_RULES]
    assert not [e for e in errors if any(rid in e for rid in ids)]
    assert errors == []


# --- BAD packs, one assertion each ----------------------------------------


def test_unknown_flag_in_a_condition_names_the_rule(tmp_path):
    rule = {"id": "shadow-falls", "when": {"starts": {}},
            "if": [{"flag": "nope", "is": True}],
            "then": [{"set": "lit"}]}
    errors = _one(tmp_path, rule)
    assert any("shadow-falls" in e and "nope" in e for e in errors)


def test_unknown_claim_in_a_belief_names_the_rule(tmp_path):
    rule = {"id": "guard-check", "when": {"starts": {}},
            "if": [{"believes": {"who": "keeper", "claim": "ghost-claim"}}],
            "then": [{"set": "lit"}]}
    errors = _one(tmp_path, rule)
    assert any("guard-check" in e and "ghost-claim" in e for e in errors)


def test_unknown_person_not_a_speaker_names_the_rule(tmp_path):
    rule = {"id": "stranger-notice", "when": {"starts": {}},
            "then": [{"say": {"who": "stranger", "line": "Who goes?"}}]}
    errors = _one(tmp_path, rule)
    assert any("stranger-notice" in e and "stranger" in e for e in errors)


def test_unknown_item_in_has_and_give_names_the_rule(tmp_path):
    rule = {"id": "lantern-hunt", "when": {"starts": {}},
            "if": [{"has": "lantern"}],
            "then": [{"give": "lantern"}]}
    errors = _one(tmp_path, rule)
    assert any("lantern-hunt" in e and "lantern" in e for e in errors)
    assert sum("lantern" in e for e in errors) == 2  # one for has, one for give


def test_unknown_place_in_enters_and_point_to_names_the_rule(tmp_path):
    rule = {"id": "wrong-door", "when": {"enters": {"place": "nowhere"}},
            "then": [{"point-to": "nowhere"}]}
    errors = _one(tmp_path, rule)
    assert any("wrong-door" in e and "nowhere" in e for e in errors)
    assert sum("nowhere" in e for e in errors) == 2  # one for enters, one for point-to


def test_unknown_event_name_names_the_rule(tmp_path):
    rule = {"id": "word-wait", "when": {"says": {"text": "hello"}},
            "then": [{"set": "lit"}]}
    errors = _one(tmp_path, rule)
    assert any("word-wait" in e and "says" in e for e in errors)


def test_unknown_condition_key_names_the_rule_and_key(tmp_path):
    rule = {"id": "sprint-on", "when": {"starts": {}},
            "if": [{"sprints": True}],
            "then": [{"set": "lit"}]}
    errors = _one(tmp_path, rule)
    assert any("sprint-on" in e and "sprints" in e for e in errors)


def test_unknown_action_key_names_the_rule_and_key(tmp_path):
    rule = {"id": "blink-away", "when": {"starts": {}},
            "then": [{"teleport": "town"}]}
    errors = _one(tmp_path, rule)
    assert any("blink-away" in e and "teleport" in e for e in errors)


def test_a_rule_with_no_id_is_reported(tmp_path):
    rule = {"when": {"starts": {}}, "then": [{"set": "lit"}]}
    errors = _one(tmp_path, rule)
    assert any("position 0" in e and "id" in e for e in errors)


def test_two_rules_with_the_same_id_name_the_id(tmp_path):
    first = {"id": "twin-rule", "when": {"starts": {}}, "then": [{"set": "lit"}]}
    second = {"id": "twin-rule", "when": {"opens": {"what": "torch"}},
              "then": [{"weather": "fog"}]}
    errors = _one(tmp_path, first, rules=[first, second])
    assert any("twin-rule" in e and "unique" in e for e in errors)


def test_a_malformed_when_names_the_rule(tmp_path):
    rule = {"id": "near-far", "when": {"comes-near": {"who": "keeper",
                                                      "distance": 12}},
            "then": [{"set": "lit"}]}
    errors = _one(tmp_path, rule)
    assert any("near-far" in e and "0..9" in e for e in errors)


def test_contact_distance_zero_is_the_players_own_shape(tmp_path):
    # The player fires tile contact at distance 0; the vocabulary says
    # so ("within N tiles", 0 = standing on it).
    rule = {"id": "on-the-stone", "when": {"comes-near": {"who": "keeper",
                                                          "distance": 0}},
            "then": [{"say": "The stone hums."}]}
    assert _one(tmp_path, rule) == []


def test_a_say_line_over_the_speech_box_limit_names_the_rule(tmp_path):
    rule = {"id": "long-wind", "when": {"starts": {}},
            "then": [{"say": {"who": "keeper", "line": "x" * 300}}]}
    errors = _one(tmp_path, rule)
    assert any("long-wind" in e and "280" in e for e in errors)


def test_more_than_forty_rules_names_how_many(tmp_path):
    rules = [{"id": f"stack-{i}", "when": {"starts": {}},
              "then": [{"set": "lit"}]} for i in range(41)]
    errors = _one(tmp_path, rules[0], rules=rules)
    assert any("41" in e and "40" in e for e in errors)


def test_two_rules_conflicting_over_one_event_name_both_ids(tmp_path):
    fog = {"id": "calls-fog", "when": {"starts": {}}, "then": [{"weather": "fog"}]}
    clear = {"id": "calls-clear", "when": {"starts": {}},
             "then": [{"weather": "clear"}]}
    errors = _one(tmp_path, fog, rules=[fog, clear])
    assert any("calls-fog" in e and "calls-clear" in e for e in errors)


def test_two_rules_showing_and_hiding_one_thing_name_both_ids(tmp_path):
    show = {"id": "opens-lid", "when": {"opens": {"what": "torch"}},
            "then": [{"show": "torch"}]}
    hide = {"id": "shuts-lid", "when": {"opens": {"what": "torch"}},
            "then": [{"hide": "torch"}]}
    errors = _one(tmp_path, show, rules=[show, hide])
    assert any("opens-lid" in e and "shuts-lid" in e for e in errors)


def test_validate_surfaces_rule_errors(tmp_path):
    """rules_errors is wired into validate(), beside the other catalogs."""
    rule = {"id": "shadow-falls", "when": {"starts": {}},
            "if": [{"flag": "nope", "is": True}],
            "then": [{"set": "lit"}]}
    pack = _pack(tmp_path, {"flags": FLAGS, "rules": [rule]})
    assert any("shadow-falls" in e for e in _validate(pack))


# --- COMPATIBILITY --------------------------------------------------------


def test_sample_world_validates_clean():
    assert _validate(SAMPLE) == []


def test_sample_world_load_carries_none_of_the_four_keys():
    w = maplab.load_pack(SAMPLE)
    assert [k for k in ("flags", "claims", "people", "rules") if k in w] == []


def test_a_copy_declaring_none_of_the_four_keys_validates_exactly_as_before(tmp_path):
    assert _validate(_copy_sample(tmp_path)) == []


# --- rules_notes: warnings, not errors ------------------------------------


def test_note_a_believed_claim_no_rule_ever_makes_true_or_false(tmp_path):
    pack = _pack(tmp_path, {"flags": FLAGS, "claims": CLAIMS, "people": PEOPLE,
                            "rules": [{"id": "unrelated-rule",
                                       "when": {"starts": {}},
                                       "then": [{"set": "lit"}]}]})
    notes = maplab.rules_notes(maplab.load_pack(pack), pack_dir=pack)
    assert any("keeper-guards-gate" in n and "never made" in n for n in notes)
    # The note must NOT fail the pack: validate() stays clean.
    assert _validate(pack) == []


def test_note_a_belief_no_rule_ever_reads(tmp_path):
    rule = {"id": "belief-setter", "when": {"starts": {}},
            "then": [{"believes": {"who": "keeper",
                                   "claim": "keeper-guards-gate"}}]}
    pack = _pack(tmp_path, {"flags": FLAGS, "claims": CLAIMS, "people": PEOPLE,
                            "rules": [rule]})
    notes = maplab.rules_notes(maplab.load_pack(pack), pack_dir=pack)
    assert any("keeper-guards-gate" in n and "read that belief" in n for n in notes)
    # The rule DOES change the claim, so the first warning stays away.
    assert not any("never made" in n for n in notes)


# --- hostile ids stay plain sentences, never paths -------------------------


def test_hostile_ids_never_touch_the_filesystem(tmp_path, monkeypatch):
    long_claim = "../" * 60 + "secret"
    rule = {"id": "../../rule/boom",
            "when": {"enters": {"place": "../../somewhere"}},
            "if": [{"believes": {"who": "../../root", "claim": "../../etc/passwd"}},
                   {"believes": {"who": "../../root", "claim": long_claim}},
                   {"flag": "..", "is": True}],
            "then": [{"say": {"who": "../../root", "line": "no"}},
                     {"give": "../item"},
                     {"set": ".."},
                     {"point-to": "../../somewhere"}]}
    pack = _pack(tmp_path, {
        "flags": {"..": "a flag name that looks like a path"},
        "claims": {},
        "people": {"../../root": {"believes": []}},
        "rules": [rule],
    })
    loaded = maplab.load_pack(pack)  # before the guard: the loader's own reads
    opened: list[Path] = []
    real_open = Path.open

    def _guarded(self, *args, **kwargs):
        opened.append(self)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _guarded)
    errors = maplab.rules_errors(loaded, pack_dir=pack)
    # Every answer is a plain sentence, and the only files touched are
    # the pack's own declared data (world.json, region contract.json) -
    # every path came from directory listings, never from pack data.
    assert errors and all(isinstance(e, str) for e in errors)
    assert any("../../rule/boom" in e for e in errors)
    for f in opened:
        assert f.is_relative_to(pack), f
        assert f.name in ("world.json", "contract.json"), f


# ---- the one identity model: everything a rule names is declared ----

def test_a_poi_label_is_a_thing_a_rule_may_name(tmp_path):
    # The player fires `comes-near`/`uses-with` with the POI's own
    # label; the label is declared in the region contract, so it IS
    # the id. No pack should have to invent a fake item for a place.
    rules = [
        {"id": "the-stone-hums",
         "when": {"comes-near": {"who": "the stone", "distance": 0}},
         "then": [{"say": "The stone hums."}]},
        {"id": "oil-on-the-stone",
         "when": {"uses-with": {"item": "chalked-map", "with": "the stone"}},
         "then": [{"set": "lit"}]},
    ]
    assert _one(tmp_path, rules[0], rules=rules) == []


def test_a_chest_book_is_a_thing_an_opens_rule_may_name(tmp_path):
    # A chest IS a library book; its id is what the interaction path
    # sends in `opens`.
    rule = {"id": "the-chest-was-a-trap",
            "when": {"opens": {"what": "the-keepers-ledger"}},
            "then": [{"say": "Something was waiting in the ledger."}]}
    assert _one(tmp_path, rule) == []


def test_the_new_events_name_their_own_ids(tmp_path):
    rules = [
        {"id": "felled", "when": {"defeats": {"what": "cellar-rat"}},
         "then": [{"set": "lit"}]},
        {"id": "closed", "when": {"reads": {"what": "no-such-book"}},
         "then": [{"set": "lit"}]},
        {"id": "watch-turns", "when": {"phase-changes": {"to": "midnight"}},
         "then": [{"set": "lit"}]},
    ]
    errors = _one(tmp_path, rules[0], rules=rules)
    for rule, needle in ((rules[0], "cellar-rat"), (rules[1], "no-such-book"),
                         (rules[2], "midnight")):
        assert any(rule["id"] in e and needle in e for e in errors), errors


def test_the_new_events_accept_declared_ids(tmp_path):
    pack = _pack(tmp_path, {
        "flags": dict(FLAGS), "claims": dict(CLAIMS), "people": dict(PEOPLE),
        "rules": [
            {"id": "felled", "when": {"defeats": {"what": "rat-1"}},
             "then": [{"set": "lit"}]},
            {"id": "bought", "when": {"buys": {"what": "chalked-map"}},
             "then": [{"set": "met-keeper"}]},
            {"id": "sold", "when": {"sells": {"what": "chalked-map"}},
             "then": [{"set": "met-keeper"}]},
            {"id": "closed", "when": {"reads": {"what": "the-keepers-ledger"}},
             "then": [{"set": "lit"}]},
            {"id": "watch-turns", "when": {"phase-changes": {"to": "dusk"}},
             "then": [{"say": "The watch turns."}]},
            {"id": "turn-in", "when": {"comes-near": {"who": "keeper", "distance": 1}},
             "then": [{"takes": "chalked-map"}, {"set": "met-keeper"}]},
        ],
    })
    # one declared enemy, in the first region's contract
    contract_path = (pack / "acts" / "act-1" / "town" / "contract.json")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["enemies"] = [{"id": "rat-1", "name": "the rat",
                            "at": [2, 2], "hp": 3, "atk": 1}]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    assert _errors(pack) == []


def test_takes_and_give_take_the_same_item_ids(tmp_path):
    rule = {"id": "hand-it-over",
            "when": {"comes-near": {"who": "keeper", "distance": 1}},
            "then": [{"takes": "no-such-thing"}]}
    errors = _one(tmp_path, rule)
    assert any("hand-it-over" in e and "takes" in e for e in errors), errors
