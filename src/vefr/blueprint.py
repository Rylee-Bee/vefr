"""Blueprint format 1 - expand a small source into enemy records.

A pack may carry a `blueprint.json` at its root: the edited truth for the
regions it owns. This module is the library half of
`docs/adr/0008-blueprint-format.md`: the versioned reader, the closed key
sets, the validator and the expander. It adds no runtime and no rule
language - a pack word grants no authority.

Format 1 is acts-shape only. `expand` returns `{region_key: [record]}`
in file order; each record's keys follow `FIELD_ORDER` and absent keys
are skipped. Nothing here reads the clock, the network or a model.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

from .maplab import load_pack

NORMALIZER_VERSION = 1

TOP_KEYS = frozenset({"blueprint", "families", "regions"})
FAMILY_KEYS = frozenset({"defaults", "extends"})
FIELD_KEYS = frozenset({"name", "sprite", "hp", "atk", "xp", "sight", "drops"})
REGION_KEYS = frozenset({"enemies"})
INSTANCE_KEYS = frozenset({"id", "family", "at", "properties"})

FIELD_ORDER = ("id", "name", "sprite", "at", "hp", "atk", "xp", "sight", "drops")


class BlueprintError(Exception):
    """A Blueprint that cannot be read or expanded.

    `str(err)` is one plain sentence; `.pointer` is the JSON pointer of
    the offending value ("" when the error names no value).
    """

    def __init__(self, message: str, pointer: str = "") -> None:
        super().__init__(message)
        self.pointer = pointer


def _esc(token: object) -> str:
    """Escape one pointer token: `~` -> `~0`, `/` -> `~1`."""
    return str(token).replace("~", "~0").replace("/", "~1")


def _check_keys(obj: dict, allowed: frozenset[str], base: str) -> None:
    """Refuse any key of `obj` that is not in `allowed`.

    `base` is the pointer of `obj` itself; the pointer of an offending
    key is `base`/escaped-key.
    """
    for key in obj:
        if key not in allowed:
            raise BlueprintError(
                f"unknown key {key!r} at {base or '/'}",
                f"{base}/{_esc(key)}",
            )


def read(path: str | Path) -> dict:
    """Parse a Blueprint JSON file and return it unchanged."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BlueprintError(f"blueprint file {path} could not be read") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise BlueprintError(f"blueprint file {path} is not valid JSON") from exc


def read_v1(source: dict) -> dict:
    """Validate a format-1 Blueprint against the closed key sets."""
    if not isinstance(source, dict):
        raise BlueprintError("blueprint must be a JSON object", "")
    version = source.get("blueprint")
    if type(version) is not int or version != 1:
        raise BlueprintError("blueprint version must be the integer 1", "/blueprint")
    _check_keys(source, TOP_KEYS, "")

    families = source.get("families", {})
    if not isinstance(families, dict):
        raise BlueprintError("families must be an object", "/families")
    for name, family in families.items():
        base = f"/families/{_esc(name)}"
        if not isinstance(family, dict):
            raise BlueprintError("a family must be an object", base)
        _check_keys(family, FAMILY_KEYS, base)
        if "extends" in family and not isinstance(family["extends"], str):
            raise BlueprintError("extends must name one family", f"{base}/extends")
        defaults = family.get("defaults", {})
        if not isinstance(defaults, dict):
            raise BlueprintError("defaults must be an object", f"{base}/defaults")
        _check_keys(defaults, FIELD_KEYS, f"{base}/defaults")

    regions = source.get("regions", {})
    if not isinstance(regions, dict):
        raise BlueprintError("regions must be an object", "/regions")
    for rkey, region in regions.items():
        base = f"/regions/{_esc(rkey)}"
        if not isinstance(region, dict):
            raise BlueprintError("a region must be an object", base)
        _check_keys(region, REGION_KEYS, base)
        enemies = region.get("enemies", [])
        if not isinstance(enemies, list):
            raise BlueprintError("enemies must be a list", f"{base}/enemies")
        for i, instance in enumerate(enemies):
            ibase = f"{base}/enemies/{i}"
            if not isinstance(instance, dict):
                raise BlueprintError("an enemy must be an object", ibase)
            _check_keys(instance, INSTANCE_KEYS, ibase)
            if not isinstance(instance.get("id"), str) or not instance["id"]:
                raise BlueprintError("enemy is missing its id (a non-empty string)", f"{ibase}/id")
            if not isinstance(instance.get("family"), str):
                raise BlueprintError("enemy must name one family as a string", f"{ibase}/family")
            at = instance.get("at")
            if at is not None and not (
                isinstance(at, list) and len(at) == 2
                and all(type(n) is int for n in at)
            ):
                raise BlueprintError("at must be [x, y] whole numbers", f"{ibase}/at")
            properties = instance.get("properties", {})
            if not isinstance(properties, dict):
                raise BlueprintError("properties must be an object", f"{ibase}/properties")
            _check_keys(properties, FIELD_KEYS, f"{ibase}/properties")
    return source


READERS = {1: read_v1}


def _declared_items(pack_dir: Path) -> set[str]:
    """The item ids the pack declares, via the loader then world.json."""
    items = None
    try:
        items = load_pack(pack_dir).get("items")
    except (OSError, ValueError, KeyError, SystemExit):
        items = None
    if not isinstance(items, dict):
        try:
            world = json.loads((pack_dir / "world.json").read_text(encoding="utf-8"))
            items = world.get("items")
        except (OSError, ValueError):
            items = None
    return set(items) if isinstance(items, dict) else set()


def _region_dir(pack_dir: Path, region_key: str, pointer: str) -> str:
    """Resolve acts/<act>/<region> under `pack_dir`, guarded by `_inside`."""
    from .cli import _inside  # lazy: cli will import this module

    parts = region_key.split("/")
    if len(parts) != 2:
        raise BlueprintError(
            f"region key {region_key!r} is not <act>/<region>", pointer
        )
    base = os.path.realpath(pack_dir)
    # Guard the raw key against the pack root first: an act of `..` makes
    # `acts/../<region>` normalise back inside the pack, so the
    # acts-relative probe alone cannot see the traversal. Then guard the
    # acts-relative directory itself. No Blueprint string becomes a path
    # except through `_inside`.
    if _inside(base, *parts) is None:
        raise BlueprintError(f"region {region_key!r} is outside the pack", pointer)
    act, region = parts
    target = _inside(base, "acts", act, region)
    if target is None:
        raise BlueprintError(f"region {region_key!r} is outside the pack", pointer)
    if not os.path.isdir(target):
        raise BlueprintError(f"region directory {region_key!r} does not exist", pointer)
    return target


def _family_record(family: str, families: dict) -> dict:
    """The merged defaults of `family` and its parent chain, root first.

    A later value replaces an earlier one whole. Every value is fresh, so
    records never share objects. Unknown parents and cycles fail with a
    pointer: a self-cycle names the family, a longer cycle names `/families`.
    """
    chain: list[str] = []
    seen: set[str] = set()
    current = family
    while True:
        if current in seen:
            if len(chain) == 1:
                raise BlueprintError(
                    f"family {current!r} extends itself (cycle)",
                    f"/families/{_esc(current)}",
                )
            raise BlueprintError("family inheritance has a cycle", "/families")
        seen.add(current)
        chain.append(current)
        parent = families[current].get("extends")
        if parent is None:
            break
        if parent not in families:
            raise BlueprintError(
                f"unknown parent {parent!r}",
                f"/families/{_esc(current)}/extends",
            )
        current = parent

    record: dict = {}
    for name in reversed(chain):
        defaults = families[name].get("defaults") or {}
        record.update(copy.deepcopy(defaults))
    return record


def expand(source: dict, *, pack_dir: str | Path) -> dict[str, list[dict]]:
    """Validate `source`, then expand it into `{region_key: [records]}`."""
    version = source.get("blueprint") if isinstance(source, dict) else None
    reader = READERS.get(version) if type(version) is int else None
    if reader is None:
        raise BlueprintError("blueprint version must be the integer 1", "/blueprint")
    source = reader(source)
    pack = Path(pack_dir)
    families = source.get("families") or {}
    regions = source.get("regions") or {}
    items = _declared_items(pack)

    out: dict[str, list[dict]] = {}
    for region_key, region in regions.items():
        rbase = f"/regions/{_esc(region_key)}"
        _region_dir(pack, region_key, rbase)
        records: list[dict] = []
        seen_ids: set = set()
        for i, instance in enumerate(region.get("enemies") or []):
            ibase = f"{rbase}/enemies/{i}"

            family = instance.get("family")
            if family not in families:
                raise BlueprintError(
                    f"unknown family {family!r}", f"{ibase}/family"
                )
            record = _family_record(family, families)
            record.update(copy.deepcopy(instance.get("properties") or {}))

            if "id" in instance:
                record["id"] = copy.deepcopy(instance["id"])
            if "at" not in instance:
                raise BlueprintError(
                    "instance is missing its at position", f"{ibase}/at"
                )
            record["at"] = copy.deepcopy(instance["at"])

            iid = instance.get("id")
            if iid in seen_ids:
                raise BlueprintError(
                    f"duplicate instance id {iid!r}", f"{ibase}/id"
                )
            seen_ids.add(iid)

            drops = record.get("drops")
            if isinstance(drops, list):
                for drop in drops:
                    if drop not in items:
                        raise BlueprintError(
                            f"unknown item {drop!r} in drops",
                            f"{ibase}/properties/drops",
                        )

            records.append({key: record[key] for key in FIELD_ORDER if key in record})
        out[region_key] = records
    return out


def canonical_hash(source: dict) -> str:
    """The SHA-256 of `source` in canonical JSON form."""
    payload = json.dumps(
        source, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode()).hexdigest()
