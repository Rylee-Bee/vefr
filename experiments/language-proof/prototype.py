"""Bounded build-time proof; not a supported pack format or runtime API."""
from copy import deepcopy
import hashlib
import json

from vefr import delve, maplab

VERSION = "proof-1"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def expand(families, instances, traits=(), items=()):
    """One explicit parent, scalar defaults; no implicit behavioral traits."""
    def defaults(name, stack=()):
        if name in stack:
            raise ValueError("family cycle")
        if name not in families:
            raise ValueError("unknown family")
        family = families[name]
        if set(family) - {"defaults", "extends"}:
            raise ValueError("unsupported family field / conflicting composition")
        base = defaults(family["extends"], (*stack, name)) if "extends" in family else {}
        return {**base, **deepcopy(family.get("defaults", {}))}

    out = []
    for instance in instances:
        if set(instance) - {"id", "family", "traits", "properties", "relations"}:
            raise ValueError("unsupported instance field")
        if not set(instance.get("traits", [])) <= set(traits):
            raise ValueError("unknown descriptive trait")
        row = {**defaults(instance["family"]), **deepcopy(instance.get("properties", {}))}
        if set(row) - {"name", "sprite", "hp", "atk", "xp", "at", "drops"}:
            raise ValueError("unsupported enemy property")
        row["id"] = instance["id"]
        for relation in instance.get("relations", []):
            if relation["type"] != "drops-on-defeat" or relation["target"] not in items:
                raise ValueError("unsupported relation or target is not an item")
            if "drops" in row:
                raise ValueError("conflicting drops defaults")
            row["drops"] = [relation["target"]]
        out.append(row)
    return out


def semantic(rule):
    """Construct a proof input from an observed rule; not a round-trip contract."""
    out = deepcopy(rule)
    out["event"] = {"type": next(iter(out["when"])), "value": next(iter(out.pop("when").values()))}
    out["effects"] = [{"type": next(iter(a)), "value": next(iter(a.values()))} for a in out.pop("then")]
    return out


def lower(source):
    out = deepcopy(source)
    event = out.pop("event")
    if event["type"] not in maplab.RULE_EVENTS:
        raise ValueError("unknown event")
    out["when"] = {event["type"]: event["value"]}
    effects = out.pop("effects")
    if any(e["type"] not in maplab.RULE_ACTION_KEYS for e in effects):
        raise ValueError("unknown effect: pack words cannot grant execution authority")
    out["then"] = [{e["type"]: e["value"]} for e in effects]
    return out


def reachable(rows):
    start = next((x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == "u")
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for p in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            a, b = p
            if 0 <= b < len(rows) and 0 <= a < len(rows[0]) and rows[b][a] != "#" and p not in seen:
                seen.add(p)
                todo.append(p)
    down = next((x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == "d")
    return down in seen, seen


def floor(seed, theme, ending=None):
    if set(theme) - {"generation", "props", "creatures", "required"}:
        raise ValueError("unknown theme property")
    if set(theme["generation"]) - {"width", "height", "rooms"}:
        raise ValueError("unsupported generator control")
    if set(theme.get("required", [])) - {"reachable-stairs", "nonblocking-dressing"}:
        raise ValueError("missing guarantee machinery")
    params = theme["generation"]
    rows = delve.generate_floor_v2(seed, **params)
    ok, cells = reachable(rows)
    if not ok:
        raise ValueError("stairs unreachable")
    available = sorted(p for p in cells if rows[p[1]][p[0]] == ".")
    revision = digest(theme)
    dress_seed = digest([seed, "dressing", revision])
    rng = delve.prng(dress_seed)
    placed = []
    requests = [("prop", p) for p in theme.get("props", [])] + [("creature", p) for p in theme.get("creatures", [])]
    if len(requests) > len(available):
        raise ValueError("impossible placement: insufficient free cells")
    for kind, value in requests:
        at = available.pop(int(rng() * len(available)))
        placed.append({"kind": kind, "value": deepcopy(value), "at": list(at)})
    up = next([x, y] for y, row in enumerate(rows) for x, c in enumerate(row) if c == "u")
    down = next([x, y] for y, row in enumerate(rows) for x, c in enumerate(row) if c == "d")
    region = delve.contract(params["width"], params["height"], up, down)
    region["enemies"] = [{**p["value"], "at": p["at"]} for p in placed if p["kind"] == "creature"]
    # Props remain metadata: no solid tiles, inventory or gameplay semantics inferred.
    return {"rows": rows, "contract": region, "dressing": placed, "authored_ending": deepcopy(ending),
            "provenance": {"layout_seed": seed, "dressing_seed": dress_seed,
                           "generator": "generate_floor_v2", "normalizer": VERSION,
                           "theme_revision": revision, "parameters": deepcopy(params)}}
