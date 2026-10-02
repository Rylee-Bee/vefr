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
import shutil
from pathlib import Path

from .maplab import load_pack

NORMALIZER_VERSION = 1

TOP_KEYS = frozenset({"blueprint", "families", "regions"})
FAMILY_KEYS = frozenset({"defaults", "extends"})
FIELD_KEYS = frozenset({"name", "sprite", "hp", "atk", "xp", "sight", "drops"})
REGION_KEYS = frozenset({"enemies"})
INSTANCE_KEYS = frozenset({"id", "family", "at", "properties"})

FIELD_ORDER = ("id", "name", "sprite", "at", "hp", "atk", "xp", "sight", "drops")


class BlueprintRefusal(ValueError):
    """A pack that must not be woven or published: its Blueprint output is
    stale or invalid. The message is the same sentence `vefr check` prints;
    the front doors print it without a traceback."""


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


# ------------------------------------------------------------------ the lock
#
# `vefr normalize` owns two things beyond the Blueprint: the generated
# `enemies` list of every region the Blueprint names, and a sidecar,
# `blueprint.lock.json`, that records what wrote them (source hash,
# normalizer and format versions, per-record provenance). Both are
# written with the same canonical serializer, so a second run over an
# unchanged Blueprint leaves identical bytes.

BLUEPRINT_FILE = "blueprint.json"
LOCK_FILE = "blueprint.lock.json"


def _write_json(path: Path, data) -> None:
    """Write JSON the way the pack writer does: 2-space, UTF-8, newline."""
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _family_chain(family, families: dict) -> list[str]:
    """The parent chain of `family`, root first.

    `expand` has already rejected unknown families and cycles, so this
    is a plain walk; an unknown name simply ends the chain.
    """
    chain: list[str] = []
    current = family
    while isinstance(current, str) and current in families and current not in chain:
        chain.append(current)
        parent = families[current].get("extends")
        current = parent if isinstance(parent, str) else None
    chain.reverse()
    return chain


def _lock_data(source: dict, expanded: dict) -> dict:
    """The lock body for one successful expansion of `source`."""
    families = source.get("families") or {}
    regions = source.get("regions") or {}
    outputs = []
    for region_key, _records in expanded.items():
        instance_list = (regions.get(region_key) or {}).get("enemies") or []
        entries = []
        for i, instance in enumerate(instance_list):
            properties = instance.get("properties")
            entries.append({
                "source": f"/regions/{_esc(region_key)}/enemies/{i}",
                "families": _family_chain(instance.get("family"), families),
                "overrides": sorted(properties) if isinstance(properties, dict) else [],
            })
        act, _, region = region_key.partition("/")
        outputs.append({
            "file": f"acts/{act}/{region}/contract.json",
            "pointer": "/enemies",
            "records": entries,
        })
    return {
        "blueprint": 1,
        "normalizer": NORMALIZER_VERSION,
        "source_sha256": canonical_hash(source),
        "outputs": outputs,
    }


def _contract_path(pack: Path, region_key: str) -> Path:
    """The guarded `contract.json` of one Blueprint-owned region.

    The region directory is resolved through `_region_dir`, which is the
    only place a Blueprint string becomes a path (`cli._inside`).
    """
    directory = _region_dir(pack, region_key, f"/regions/{_esc(region_key)}")
    return Path(directory) / "contract.json"


def check_errors(pack_dir) -> list[str]:
    """Every Blueprint problem in `pack_dir` as plain sentences.

    Empty when the pack carries neither a Blueprint nor a lock - and in
    that case nothing else is read. A present Blueprint is checked for
    the acts shape, its lock, the reader/normalizer versions, and
    freshness (the lock's source hash and every owned `enemies` list
    against what this VEFR expands now). Stale messages name the file
    and the record pointer so the author knows what to run.
    """
    pack = Path(pack_dir)
    source_path = pack / BLUEPRINT_FILE
    lock_path = pack / LOCK_FILE
    has_source = source_path.is_file()
    has_lock = lock_path.is_file()
    if not has_source and not has_lock:
        return []
    # Format 1 is acts-shape only: a flat pack with a Blueprint is
    # refused before the lock is even considered.
    if has_source and not (pack / "acts").is_dir():
        return [f"a Blueprint needs an acts/ directory, but {pack} has none"]
    if has_source and not has_lock:
        return [f"blueprint.json has no blueprint.lock.json beside it - "
                f"run 'vefr normalize --pack {pack} --out {pack}'"]
    if has_lock and not has_source:
        return ["blueprint.lock.json has no blueprint.json beside it - "
                "delete the lock or restore the Blueprint"]

    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [f"{lock_path.name} is not valid JSON"]
    if not isinstance(lock, dict):
        return [f"{lock_path.name} must be a JSON object"]

    # A format or normalizer this VEFR does not know can produce output
    # this VEFR cannot compare honestly, so it fails before expanding.
    known_formats = sorted(READERS)
    newer: list[str] = []
    normalizer = lock.get("normalizer")
    if type(normalizer) is int and normalizer > NORMALIZER_VERSION:
        newer.append(
            f"blueprint.lock.json was written by a newer normalizer "
            f"({normalizer}); this VEFR knows {NORMALIZER_VERSION}")
    version = lock.get("blueprint")
    if type(version) is int and version > max(known_formats):
        newer.append(
            f"blueprint.lock.json names a newer format ({version}); "
            f"this VEFR reads {known_formats}")
    if newer:
        return newer

    try:
        source = read(source_path)
        expanded = expand(source, pack_dir=pack)
    except BlueprintError as exc:
        return [f"blueprint: {exc} ({exc.pointer})"]

    errors: list[str] = []
    if lock.get("source_sha256") != canonical_hash(source):
        errors.append(
            "blueprint output is stale: the Blueprint changed since "
            "blueprint.lock.json was written - run 'vefr normalize "
            f"--pack {pack} --out {pack}'")
    for region_key, records in expanded.items():
        rel = f"acts/{region_key}/contract.json"
        pointer = "/enemies"
        try:
            contract = json.loads(
                _contract_path(pack, region_key).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            errors.append(f"{rel}: {pointer} is stale (the contract could not "
                          f"be read) - run 'vefr normalize --pack {pack} "
                          f"--out {pack}'")
            continue
        on_disk = contract.get("enemies") if isinstance(contract, dict) else None
        if on_disk == records:
            continue
        # Name the first differing record when the lists line up; a
        # differing length or shape can only name the list itself.
        if isinstance(on_disk, list) and len(on_disk) == len(records):
            for i, (committed, wanted) in enumerate(zip(on_disk, records)):
                if committed != wanted:
                    pointer = f"/enemies/{i}"
                    break
        errors.append(f"{rel}: {pointer} is stale (the committed value "
                      f"differs from what this VEFR expands) - run "
                      f"'vefr normalize --pack {pack} --out {pack}'")
    return errors


def notes(pack_dir) -> list[str]:
    """A note when an older normalizer wrote a still-equal lock.

    Not an error (the output matches): the author is told to re-run
    `vefr normalize` to refresh the recorded version. Empty for a pack
    with no Blueprint and no lock, or a current one.
    """
    pack = Path(pack_dir)
    source_path = pack / BLUEPRINT_FILE
    lock_path = pack / LOCK_FILE
    if not source_path.is_file() or not lock_path.is_file():
        return []
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(lock, dict):
        return []
    normalizer = lock.get("normalizer")
    if type(normalizer) is int and normalizer < NORMALIZER_VERSION:
        return [f"blueprint.lock.json was written by normalizer {normalizer}; "
                f"re-run 'vefr normalize --pack {pack} --out {pack}'"]
    return []


class NormalizeResult:
    """What `normalize` wrote, or (read-only) what it found.

    `fresh` is True only when the committed output already matches;
    `errors` are plain sentences (whole-pack validation errors on a
    refresh); `regions` maps each owned region key to its record count.
    """

    def __init__(self, fresh: bool, errors: list[str],
                 regions: dict[str, int]) -> None:
        self.fresh = fresh
        self.errors = errors
        self.regions = regions


def normalize(pack_dir, out=None) -> NormalizeResult:
    """Validate and expand a Blueprint, optionally writing the output.

    `out` None is read-only. `out` equal to the pack refreshes it in
    place, restoring the previous bytes if the whole-pack validation
    fails. Any other `out` must not exist or be an empty directory: the
    pack is copied there, refreshed and validated there, and the
    original is never touched.
    """
    pack = Path(pack_dir)
    if out is None:
        return _normalize_read_only(pack)
    out_path = Path(out)
    if os.path.realpath(out_path) == os.path.realpath(pack):
        return _refresh_in_place(pack)
    return _normalize_copy(pack, out_path)


def _region_counts(expanded: dict) -> dict[str, int]:
    return {key: len(records) for key, records in expanded.items()}


def _normalize_read_only(pack: Path) -> NormalizeResult:
    errors = check_errors(pack)
    regions: dict[str, int] = {}
    source_path = pack / BLUEPRINT_FILE
    if source_path.is_file():
        try:
            expanded = expand(read(source_path), pack_dir=pack)
        except BlueprintError:
            pass
        else:
            regions = _region_counts(expanded)
    return NormalizeResult(not errors, errors, regions)


def _normalize_copy(pack: Path, out: Path) -> NormalizeResult:
    real_pack, real_out = os.path.realpath(pack), os.path.realpath(out)
    if real_out == real_pack or real_out.startswith(real_pack + os.sep):
        return NormalizeResult(
            False, [f"output directory {out} is inside the pack - choose "
                    "a directory outside it"], {})
    created = not out.exists()
    if not created:
        if not out.is_dir():
            return NormalizeResult(
                False, [f"output path {out} is not a directory"], {})
        if any(out.iterdir()):
            return NormalizeResult(
                False,
                [f"output directory {out} is not empty - refusing to write "
                 "into it"],
                {})
    try:
        # symlinks=True keeps a link as a link: a pack must never pull a
        # file from outside itself into the copy.
        shutil.copytree(pack, out, symlinks=True, dirs_exist_ok=True)
    except OSError as exc:
        _discard(out, created)
        return NormalizeResult(False, [f"could not copy {pack} to {out}: {exc}"], {})
    result = _refresh_in_place(out)
    if result.errors:
        _discard(out, created)  # a failed refresh leaves nothing behind
    return result


def _discard(out: Path, created: bool) -> None:
    """Remove what `_normalize_copy` wrote: the directory it made, or the
    contents of the empty directory it was given."""
    if created:
        shutil.rmtree(out, ignore_errors=True)
        return
    for child in out.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)


def _restore(backups: dict) -> None:
    """Put every touched file back, deleting one that did not exist before."""
    for path, data in backups.items():
        if data is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(data)


def _refresh_in_place(pack: Path) -> NormalizeResult:
    source_path = pack / BLUEPRINT_FILE
    lock_path = pack / LOCK_FILE
    if not source_path.is_file():
        return NormalizeResult(
            False, [f"{source_path} does not exist - nothing to normalize"], {})
    try:
        source = read(source_path)
        expanded = expand(source, pack_dir=pack)
    except BlueprintError as exc:
        return NormalizeResult(False, [f"blueprint: {exc} ({exc.pointer})"], {})
    regions = _region_counts(expanded)

    owned: list[tuple[Path, list]] = []
    try:
        for region_key, records in expanded.items():
            owned.append((_contract_path(pack, region_key), records))
    except BlueprintError as exc:
        return NormalizeResult(False, [f"blueprint: {exc} ({exc.pointer})"], regions)

    # Snapshot every file this refresh will touch before touching any of
    # them, so a failing whole-pack validation can put the pack back.
    backups: dict[Path, bytes | None] = {}
    for contract, _records in owned:
        backups[contract] = contract.read_bytes() if contract.is_file() else None
    backups[lock_path] = lock_path.read_bytes() if lock_path.is_file() else None

    for contract, records in owned:
        contract_data: dict = {}
        if contract.is_file():
            try:
                loaded = json.loads(contract.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                loaded = {}
            if isinstance(loaded, dict):
                contract_data = loaded
        contract_data["enemies"] = records
        _write_json(contract, contract_data)
    _write_json(lock_path, _lock_data(source, expanded))

    # The whole normalized pack, through today's validator (which now
    # also runs this module's freshness check): only this second pass
    # can see cross-references.
    from .maplab import validate as _validate

    try:
        errors = _validate(load_pack(pack), pack_dir=pack)
    except Exception:
        _restore(backups)
        raise
    if errors:
        _restore(backups)
        return NormalizeResult(False, errors, regions)
    return NormalizeResult(True, [], regions)
