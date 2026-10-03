from copy import deepcopy
import pytest
from prototype import expand, floor, lower, semantic


def test_family_defaults_override_and_drop():
    f = {"small": {"defaults": {"name": "creature", "hp": 3, "atk": 1}}}
    assert expand(f, [{"id": "one", "family": "small", "properties": {"hp": 5, "at": [2, 3]},
                       "relations": [{"type": "drops-on-defeat", "target": "key"}]}], items=["key"]) == [
        {"id": "one", "name": "creature", "hp": 5, "atk": 1, "at": [2, 3], "drops": ["key"]}]


@pytest.mark.parametrize("kind", ["trait", "family", "target", "conflict", "cycle", "composition"])
def test_family_rejects(kind):
    f = {"small": {"defaults": {"hp": 3}}}
    i = {"id": "one", "family": "small"}
    if kind == "trait":
        i["traits"] = ["undeclared"]
    elif kind == "family":
        i["family"] = "missing"
    elif kind == "target":
        i["relations"] = [{"type": "drops-on-defeat", "target": "person"}]
    elif kind == "conflict":
        f["small"]["defaults"]["drops"] = ["old"]
        i["relations"] = [{"type": "drops-on-defeat", "target": "key"}]
    elif kind == "cycle":
        f["small"]["extends"] = "small"
    else:
        f["small"]["mixins"] = ["a", "b"]
    with pytest.raises(ValueError):
        expand(f, [i], items=["key"])


def test_lower_preserves_and_rejects_authority():
    rule = {"id": "r", "when": {"starts": {}}, "then": [{"say": "hello"}], "once": True}
    assert lower(semantic(rule)) == rule
    source = semantic(rule)
    source["effects"] = [{"type": "teleport-through-time", "value": {}}]
    with pytest.raises(ValueError):
        lower(source)


def test_floor_determinism_and_failures():
    t = {"generation": {"width": 30, "height": 20, "rooms": 8}, "props": ["mark"],
         "required": ["reachable-stairs", "nonblocking-dressing"]}
    ending = {"to": "authored-end", "at": [1, 1]}
    a = floor("proof", t, ending)
    assert a == floor("proof", t, ending)
    assert a["authored_ending"] == ending
    changed = deepcopy(t)
    changed["props"].append("other")
    assert floor("proof", changed)["rows"] == a["rows"]
    for bad in [{**t, "required": ["signature-room"]},
                {**t, "generation": {**t["generation"], "corridor_width": 2}},
                {**t, "props": ["mark"] * 1000}]:
        with pytest.raises(ValueError):
            floor("proof", bad)
