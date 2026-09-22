"""The world pack loader - the seam between the engine and the story.

The engine (src/vefr) never hardcodes world content. Everything the
story owns - phases, voices, bonds, regions (town and dungeon), the
surface - lives in a pack directory. Two shapes are supported:

  Flat shape (legacy / simple packs):
    worlds/<name>/
      world.json
      logbok.md
      ledger.md
      map.md
      voices/*.md                 # speaker voice prompts
      voices/<name>.fragments.md  # optional: speakable lines for
                                  # offline play (bullet lines)

  Acts shape (multi-region, self-contained per act):
    worlds/<name>/
      world.json              # engine contract: title, phases, surface, acts[]
      logbok.md               # pack-level canon (shared across acts)
      ledger.md               # pack-level voice anchors (shared)
      acts/
        act-1/
          world.json          # act-level contract: id, title, regions, speakers,
                              #   enemies, bosses, transitions, vault_intro
          town/
            map.md
            voices/*.md
            sprites/*
          dungeon/
            map.md
            voices/*.md
            sprites/*

The loader returns a single canonical shape regardless of which on-disk
shape the pack uses: top-level keys are the world's metadata (title,
phases, surface, logbok, ledger, acts), and `acts` is ALWAYS a list
with at least one element. Flat packs are loaded as a single implicit
act so every consumer can use the same access pattern.

  world = load_world()
  world["title"]                          # the world's title
  world["phases"]                         # {whispers: ..., doubts: ..., ...}
  world["surface"]                        # "combat" | "investigation" | "plain"
  world["acts"]                           # [act1, act2, ...] - always a list
  world["_current_act"]                   # 0 for now; future PRs advance this
  current_act(world)                      # world["acts"][world["_current_act"]]
  current_act(world)["regions"]["town"]   # the town of the active act

SURFACE: world.json may declare a 'surface' field - one of 'combat',
'investigation', 'plain'. The surface is the *grammar* the player
sees (HP bars, encounter prompts, investigation dice), not the
engine's actual behavior. The engine never gates the player on HP,
attack, or roll results - the surface is a costume over the
underlying rumor engine. Default surface is 'combat' for
back-compat with existing packs.

JOURNEY: the engine's story structure is the Hero's Journey, told
through four Elder Futhark runes. The mapping lives in journey.py.
Packs can rename their phases (any keys the author wants) but the
journey-stage anchors are positional - first phase in `phases` maps
to the first rune, and so on.

STEFNA / BELL VOICE: a pack may declare an optional top-level
`stefna_voice` (string naming which speaker writes the sealed letter;
absent means "the pack's first declared voice"). Every voice declared
in the pack must carry a non-empty `strike` string prompt for that
letter.

VOICES CONVENTION: flat packs place voice prompt files at pack-level
`voices/<name>.md`. Acts-shaped packs place them at the region level
under `acts/<id>/<region>/voices/<name>.md`, discovered by convention
matching the file stem. Flat and acts resolution is unified via
`resolve_voice_file()`.

VISIBLE ENGINE: every load step is recorded to the weave log so the
author can see exactly what the loader did. See weave.py.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from .paths import pack_dir
from .weave import weave

log = logging.getLogger(__name__)

VALID_SURFACES = ("combat", "investigation", "plain")
REQUIRED_FLAT = ("title", "phases", "voices", "bonds", "town")


def creed_from(config: dict) -> str:
    """The world's creed - the one governing line of a pack.

    `gold_rule` is the pre-rename field name (the term belonged to one
    author's game). It is read forever so packs written before the
    rename keep their line; maplab writes the value back as `creed`.
    """
    return config.get("creed") or config.get("gold_rule", "")


class PackError(RuntimeError):
    """A world pack failed to load. The error message names the pack
    and the cause so the author can fix it without reading the stack."""


def _read_json(path: Path, *, what: str) -> dict:
    if not path.exists():
        raise PackError(f"missing {what}: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PackError(f"invalid JSON in {what} ({path}): {e}") from e


def _read_text(path: Path, *, what: str) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _discover_voices(voices_dir: Path) -> dict:
    """Convention: every *.md under voices/ is a speaker voice file,
    named by the file's stem. The loader returns {stem: content}.
    `<stem>.fragments.md` files are NOT voices - they are the
    speaker's offline whisper bank (see _discover_fragments)."""
    if not voices_dir.is_dir():
        return {}
    out = {}
    for sf in sorted(voices_dir.glob("*.md")):
        if sf.name.endswith(".fragments.md"):
            continue
        out[sf.stem] = sf.read_text(encoding="utf-8")
    return out


def _discover_fragments(voices_dir: Path) -> dict:
    """Convention: `<name>.fragments.md` beside a voice file carries
    that speaker's speakable fragments - short lines the author
    writes by hand so a packaged game with no woven pool and no
    model can still hear them. Bullet lines speak; every other line
    is a note to the author. The loader returns
    {name: [lines]} with the `.fragments` suffix stripped. Optional
    per voice: a pack without fragment banks keeps the honest
    silence it has always had."""
    if not voices_dir.is_dir():
        return {}
    out: dict[str, list[str]] = {}
    for sf in sorted(voices_dir.glob("*.fragments.md")):
        lines: list[str] = []
        for raw in sf.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("- ") and len(line) > 2:
                lines.append(line[2:].strip())
        if lines:
            out[sf.name[: -len(".fragments.md")]] = lines
    return out


def fragments_for_pack(pack: Path) -> dict[str, list[str]]:
    """Every fragment bank in a pack, by speaker key.

    Walks the same convention voice discovery walks - the pack
    root's voices/ (flat shape) plus every act region's voices/
    (acts shape) - so a region's fragment bank travels with its
    own speakers. Later files never override earlier lines: banks
    with the same speaker key merge in file order, deduplicated.
    """
    out: dict[str, list[str]] = {}
    roots = [pack / "voices"]
    acts_dir = pack / "acts"
    if acts_dir.is_dir():
        for act_dir in sorted(acts_dir.iterdir()):
            if not act_dir.is_dir() or act_dir.name.startswith("."):
                continue
            for region_dir in sorted(act_dir.iterdir()):
                if region_dir.is_dir() and (region_dir / "voices").is_dir():
                    roots.append(region_dir / "voices")
    for root in roots:
        for key, lines in _discover_fragments(root).items():
            merged = out.setdefault(key, [])
            for ln in lines:
                if ln not in merged:
                    merged.append(ln)
    return out


def _discover_sprites(sprites_dir: Path) -> dict:
    """Convention: every file under sprites/ is a named sprite. The
    loader returns {name: relative_path}. The web layer resolves the
    path against the act's static mount."""
    if not sprites_dir.is_dir():
        return {}
    out = {}
    for f in sorted(sprites_dir.rglob("*")):
        if f.is_file():
            out[f.stem] = str(f.relative_to(sprites_dir))
    return out


def _load_region(region_dir: Path, *, region_name: str, act_id: str) -> dict:
    """Load one region (town or dungeon) from its directory.

    Convention: a region directory has map.md, optionally voices/
    and sprites/, and optionally a `contract.json` for region
    metadata (legend, watch, sanctuary_tiles, etc.) that used
    to live inline in the act's world.json. The loader picks up
    whatever is there - the engine never requires the contract
    file, but a multi-region pack is much more useful with it.
    """
    if not region_dir.is_dir():
        weave("region.missing", act=act_id, region=region_name,
              hint=f"no directory at {region_dir}")
        return {"map_text": "", "voices": {}, "fragments": {},
                "sprites": {}, "contract": {}}

    map_text = _read_text(region_dir / "map.md",
                          what=f"{act_id}/{region_name}/map.md")
    voices = _discover_voices(region_dir / "voices")
    fragments = _discover_fragments(region_dir / "voices")
    sprites = _discover_sprites(region_dir / "sprites")
    contract: dict = {}
    contract_path = region_dir / "contract.json"
    if contract_path.exists():
        contract = _read_json(contract_path,
                              what=f"{act_id}/{region_name}/contract.json")

    weave("region.loaded", act=act_id, region=region_name,
          map_lines=len(map_text.splitlines()) if map_text else 0,
          speakers=len(voices), sprites=len(sprites),
          has_contract=bool(contract))
    return {
        "map_text": map_text,
        "voices": voices,
        "fragments": fragments,
        "sprites": sprites,
        "contract": contract,
    }


def _load_act(act_dir: Path) -> dict:
    """Load one act from its directory. Returns the act dict.

    Self-contained: each act carries its own regions, speakers,
    enemies, bosses, transitions, vault_intro. The pack-level
    logbok/ledger are inherited at read time by the consumer.
    """
    if not act_dir.is_dir():
        raise PackError(f"act directory does not exist: {act_dir}")

    contract = _read_json(act_dir / "world.json",
                          what=f"{act_dir.name}/world.json")
    act_id = contract.get("id") or act_dir.name

    required = ("id", "title", "regions")
    missing = [k for k in required if k not in contract]
    if missing:
        raise PackError(
            f"act '{act_id}' is missing required keys: {missing}"
        )

    regions = {}
    for region_name in contract["regions"]:
        region_dir = act_dir / region_name
        regions[region_name] = _load_region(region_dir,
                                            region_name=region_name,
                                            act_id=act_id)

    act = {
        "id": act_id,
        "title": contract["title"],
        "regions": regions,
        "speakers": contract.get("speakers", {}),
        "enemies": contract.get("enemies", []),
        "bosses": contract.get("bosses", []),
        "transitions": contract.get("transitions", []),
        "vault_intro": contract.get("vault_intro", ""),
        "verbs": contract.get("verbs", []),
    }
    weave("act.loaded", act=act_id, title=act["title"],
          regions=list(regions.keys()),
          speakers=len(act["speakers"]),
          enemies=len(act["enemies"]),
          bosses=len(act["bosses"]),
          transitions=len(act["transitions"]))
    return act


def _flat_to_act(config: dict, pack: Path) -> dict:
    """Convert a legacy flat-shape world.json into the always-array
    shape's single implicit act. The flat shape is:

      { title, phases, voices, bonds, speakers, surface, town, ... }

    The act form is:

      { id: <pack name>, title, regions: {town: <town dict>},
        speakers, enemies: [], bosses: [], transitions: [], ... }

    The legacy `voices` block (each speaker's full system prompt)
    and `speakers` block (NPC positions + seeds) are kept separate
    in the flat shape. In the act form, the speaker's `voice_file`
    pointer resolves to a region voice file (convention).
    """
    town = config.get("town", {})
    town_region = {
        "map_text": _read_text(pack / "map.md", what=f"{pack.name}/map.md"),
        "voices": _discover_voices(pack / "voices"),
        "fragments": _discover_fragments(pack / "voices"),
        "sprites": _discover_sprites(pack / "sprites"),
    }
    return {
        "id": pack.name,
        "title": config["title"],
        "regions": {"town": town_region},
        "speakers": config.get("speakers", {}),
        "enemies": config.get("enemies", []),
        "bosses": config.get("bosses", []),
        "transitions": config.get("transitions", []),
        "vault_intro": config.get("vault_intro", ""),
        "verbs": config.get("verbs", []),
        "_town_legacy": town,
    }


def _attach_journey(world: dict) -> None:
    """Attach the journey-stage anchors to each phase by position.
    The pack's `phases` dict is ordered (Python 3.7+ preserves
    insertion order); we zip it with journey.py's DEFAULT_PHASES.
    Packs that rename phases still get the engine's bones.
    """
    from .journey import DEFAULT_PHASES, PHASE_JOURNEY_RUNE
    world["_journey"] = []
    phase_keys = list(world["phases"].keys())
    if len(phase_keys) < len(DEFAULT_PHASES):
        return
    for i, stage_key in enumerate(DEFAULT_PHASES):
        world["_journey"].append({
            "pack_phase": phase_keys[i],
            **PHASE_JOURNEY_RUNE[stage_key],
        })


def _apply_surface(world: dict, pack_name: str) -> None:
    if "surface" not in world:
        world["surface"] = "combat"
    elif world["surface"] not in VALID_SURFACES:
        raise PackError(
            f"world pack '{pack_name}' has invalid surface "
            f"{world['surface']!r}; expected one of {VALID_SURFACES}"
        )


@lru_cache(maxsize=8)
def load_world(name: str | None = None) -> dict:
    """Load a world pack. Returns the always-array canonical shape.

    Cached: 8 entries, by pack name. Callers that need to bust the
    cache (testing, builder edits) should call `load_world.cache_clear()`.

    The pack directory comes from `pack_dir()`, which prefers the
    read-write canon mount (`/app/worlds/<name>/`) and falls back
    to the read-only template mount (`/app/worlds-template/<name>/`).
    This means an author's edits in the rw volume always win over
    any engine template that happens to share a pack name.
    """
    from .paths import pack_dir as _pack_dir, template_dir as _tdir, worlds_dir as _wdir
    d = _pack_dir(name)
    # `source` is 'canon' when the pack resolved to the rw mount,
    # 'template' when it fell back to the ro one. We compare
    # `d.parent` against the resolved template/worlds dirs so
    # the dev-box layout (where neither path is exactly /app/...)
    # still reports the right source.
    try:
        d.parent.samefile(_wdir())
        source = "canon"
    except (FileNotFoundError, OSError):
        try:
            d.parent.samefile(_tdir())
            source = "template"
        except (FileNotFoundError, OSError):
            source = "dev"
    weave("pack.load.start", pack=d.name, path=str(d), source=source)

    if not d.is_dir():
        raise PackError(f"pack directory does not exist: {d}")

    # Acts shape: worlds/<name>/world.json + worlds/<name>/acts/<id>/
    pack_contract_path = d / "world.json"
    acts_dir = d / "acts"
    if acts_dir.is_dir():
        config = _read_json(pack_contract_path, what=f"{d.name}/world.json")
        acts = []
        for act_dir in sorted(acts_dir.iterdir()):
            if not act_dir.is_dir() or act_dir.name.startswith("."):
                continue
            acts.append(_load_act(act_dir))
        if not acts:
            raise PackError(f"pack '{d.name}' has acts/ but no act subdirectories")
        # Synthesize a `_town_legacy` block on the first act from
        # its region's contract.json + map. This is what the
        # validator and older tests read; it keeps the public
        # shape stable as the on-disk layout migrates from
        # inline `town: { ... }` to per-region `town/contract.json`
        # + `town/map.md`.
        first_act = acts[0]
        first_region = next(iter(first_act["regions"].values()), None)
        if first_region is not None:
            legacy = dict(first_region.get("contract", {}))
            # The map is in map_text (a string) in the acts shape;
            # the validator wants a list of rows. Convert.
            map_text = first_region.get("map_text", "")
            if map_text and "map" not in legacy:
                legacy["map"] = [ln for ln in map_text.splitlines() if ln.strip()]
            first_act["_town_legacy"] = legacy
    else:
        # Flat shape: worlds/<name>/world.json with legacy keys.
        config = _read_json(pack_contract_path, what=f"{d.name}/world.json")
        missing = [k for k in REQUIRED_FLAT if k not in config]
        if missing:
            raise PackError(
                f"world pack '{d.name}' is missing required keys: {missing}"
            )
        acts = [_flat_to_act(config, d)]

    # Pack-level metadata - shared across all acts.
    world = {
        "name": d.name,
        "title": config.get("title") or acts[0]["title"],
        "description": config.get("description", ""),
        "creed": creed_from(config),
        "phases": config["phases"],
        "logbok": _read_text(d / "logbok.md", what=f"{d.name}/logbok.md"),
        "ledger": _read_text(d / "ledger.md", what=f"{d.name}/ledger.md"),
        "voices": config.get("voices", {}),
        "fragments": fragments_for_pack(d),
        "bonds": config.get("bonds", {}),
        "bond_draw": config.get("bond_draw", ""),
        "forge_texture": config.get("forge_texture", ""),
        "surface": config.get("surface", "combat"),
        "acts": acts,
        "_current_act": 0,
        "_shape": "acts" if acts_dir.is_dir() else "flat",
    }
    _apply_surface(world, d.name)
    _attach_journey(world)
    weave("pack.load.end", pack=d.name, acts=len(acts),
          shape=world["_shape"], surface=world["surface"])
    return world


def current_act(world: dict | None = None) -> dict:
    """Return the active act. The default index is world["_current_act"]
    (0 for the first PR; future PRs advance it via journal events).
    """
    if world is None:
        world = load_world()
    idx = world.get("_current_act", 0)
    return world["acts"][idx]


def current_town(world: dict | None = None) -> dict:
    """The town region of the current act. Convenience for the
    single-region case (the first PR): a flat pack has only the
    `town` region.
    """
    act = current_act(world)
    return act["regions"].get("town", {})


def resolve_voice_file(rel: str, world: dict | None = None) -> Path:
    """Find a voice file by relative path. Convention-driven search:

      1. acts/<current>/<region>/voices/<basename>     (convention)
      2. pack_root/<rel>                              (flat fallback)

    The speaker's `voice_file` field is a short stem in the new
    shape ("voices/keeper.md" -> "keeper.md" in the region's
    voices dir). The fallback lets flat packs keep working
    unchanged. Raises PackError if the file does not exist.
    """
    if world is None:
        world = load_world()
    act = current_act(world)
    pack_name = world.get("name") or world.get("title") or "pack"
    pack = pack_dir(world["name"])
    basename = Path(rel).name
    acts_root = pack / "acts" / act["id"]
    if acts_root.is_dir():
        for region_dir in acts_root.iterdir():
            if not region_dir.is_dir():
                continue
            candidate = region_dir / "voices" / basename
            if candidate.exists():
                return candidate
    legacy = pack / rel
    if legacy.exists():
        return legacy
    raise PackError(f"pack '{pack_name}' missing voice file for '{rel}' (looked in {acts_root} and {legacy})")


def phase_tone(phase: str, world: dict | None = None) -> str:
    """The prose tone the engine threads into every generation for
    the given phase. The pack's own `phases` dict is the source."""
    if world is None:
        world = load_world()
    phases = world["phases"]
    if phase in phases:
        return phases[phase]
    return next(iter(phases.values()))


def pack_phase_to_journey(phase_key: str,
                          world: dict | None = None) -> dict[str, str] | None:
    """Look up the journey-stage for a pack's phase key by position.
    Returns None if the pack has fewer phases than journey stages
    (a partial pack is allowed but doesn't anchor every stage).
    """
    if world is None:
        world = load_world()
    for entry in world.get("_journey", []):
        if entry["pack_phase"] == phase_key:
            return entry
    return None


def discover_packs() -> list[dict]:
    """Every pack the engine can see, with the source marked.

    Walks both the read-write canon mount and the read-only template
    mount, dedupes by name (canon wins on conflict), and returns a
    list of {name, source, path} dicts. The /api/builder/worlds
    route uses this to populate the world picker.

    The list is sorted by name, not by source, so the picker is
    stable. Engine templates sit next to the author's canon in
    the same list; the source tag tells the author which is
    which.
    """
    from .paths import template_dir, worlds_dir
    seen: dict[str, dict] = {}
    for source, base in (("canon", worlds_dir()), ("template", template_dir())):
        if not base.is_dir():
            continue
        for p in sorted(base.glob("*/world.json")):
            pack_name = p.parent.name
            if pack_name in seen:
                # Canon beats template - if both have the same pack
                # name, keep the canon entry.
                continue
            seen[pack_name] = {
                "name": pack_name,
                "source": source,
                "path": str(p.parent),
            }
    return sorted(seen.values(), key=lambda d: d["name"])
