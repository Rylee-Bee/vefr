"""norns chat - the conversational world-builder.

Copies worlds/sample-world/ as a known-good scaffold, then interviews
the author segment by segment (title, canon, theme colors, phases,
bonds, speakers) and drafts prose with the local model.

The conversation's *shape* is deterministic Python, never the model's
choice - which question comes next, whether a rename is structurally
safe, whether the pack validates. The model only ever fills in prose
inside a schema it cannot escape.

v2 grows the map and the town's people:

  - the map: the model proposes run-length rows (build_map's own
    format) at the scaffold's exact dimensions, using only the
    scaffold's legend characters. The proposal never touches the
    pack until maplab.validate() passes on a copy - two tries, then
    the scaffold's proven layout stays and the author is told so.
  - speakers: the town is no longer capped at one voice. Extra
    speakers get model-drafted names-to-lines, but their tile is
    chosen by deterministic code: reachable from the hero's start,
    not on anyone's spot, not on flood ground. No tile, no speaker.

Every write ends with maplab.validate() - the author never has to
trust their own edits, the tool always checks.

The new pack is written in the scaffold's shape (flat or acts).
The scaffold source can be either shape - maplab.load_pack unifies
them on read.
"""

import copy
import re
import shutil
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError

from . import generator, maplab

PROSE_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
}

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

THEME_SCHEMA = {
    "type": "object",
    "properties": {
        "bg": {"type": "string"},
        "hero_color": {"type": "string"},
        "deco_color": {"type": "string"},
    },
    "required": ["bg", "hero_color", "deco_color"],
}

THEME_SYSTEM = (
    "You choose a color palette for a quiet, dark, migraine-safe game "
    "UI. Every color must be a 6-digit hex code. The background must "
    "stay dark and low-saturation (near-black, muted). The protagonist "
    "color must read clearly against that dark background. The accent "
    "color is a small warm highlight, never neon, never fully "
    "saturated. Reply with only the JSON object: bg, hero_color, "
    "deco_color."
)


class Theme(BaseModel):
    bg: str
    hero_color: str
    deco_color: str


class MapRows(BaseModel):
    """Run-length rows in build_map's own format: [[["H", 4], ...], ...]."""

    rows: list[list[list]]

    def to_segments(self) -> list:
        return [[list(part) for part in row] for row in self.rows]


ASSISTANT_SYSTEM = (
    "You are a warm, curious world-building collaborator helping someone "
    "shape their own story. Plain prose, never purple, never a lecture. "
    "Write only what's asked, nothing more."
)


class Draft(BaseModel):
    text: str


def draft(prompt: str, system: str = ASSISTANT_SYSTEM) -> str:
    """One LLM call, schema-constrained to a single text field.

    Falls back to a plain placeholder if the model fails twice - the
    author always gets something to edit, never a crash mid-interview.
    """
    payload = {
        "model": generator.MODEL,
        "system": system,
        "prompt": f"{prompt} Reply with only the JSON object.",
        "format": PROSE_SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.85},
    }
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            return Draft.model_validate_json(raw).text
        except (httpx.HTTPError, generator.GeneratorUnavailable,
                generator.GeneratorFailed, ValidationError, KeyError, ValueError):
            continue
    return "(draft failed - edit this by hand)"


def draft_theme(mood: str) -> dict | None:
    """Three hex colors, schema-constrained, hex-validated on the way
    back out. Returns None on any failure - the caller keeps the
    scaffold's colors, which are already proven safe."""
    payload = {
        "model": generator.MODEL,
        "system": THEME_SYSTEM,
        "prompt": (
            f"The mood is: {mood}. Reply with only the JSON object: bg, hero_color, deco_color."
        ),
        "format": THEME_SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.7},
    }
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            colors = Theme.model_validate_json(raw)
            if all(HEX_RE.match(v) for v in (colors.bg, colors.hero_color, colors.deco_color)):
                return colors.model_dump()
        except (httpx.HTTPError, generator.GeneratorUnavailable,
                generator.GeneratorFailed, ValidationError, KeyError, ValueError):
            continue
    return None


MAP_SYSTEM = (
    "You redesign a small game town map. The map is a grid drawn as "
    "run-length rows: each row is a list of [character, count] pairs, "
    "and the counts in a row must sum to the grid's width. You may only "
    "use the legend characters you are given, with the meanings they "
    "have there. Paths must stay connected: every speaker's spot, the "
    "hero's start, and every door must be reachable through walkable "
    "characters. Keep the same dimensions. Reply with only the JSON "
    "object: rows."
)


def _map_schema(legend: dict) -> dict:
    return {
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": [
                            {"type": "string", "enum": sorted(legend.keys())},
                            {"type": "integer", "minimum": 1},
                        ],
                    },
                },
            }
        },
        "required": ["rows"],
    }


def propose_map(story: str, mood: str, w: dict, dest: Path) -> list[str] | None:
    """The interview's map growth, gated hard.

    The model proposes run-length rows at the scaffold's exact
    dimensions using only the scaffold's legend characters. A proposal
    is never returned until maplab.validate() passes on a deep copy
    with it in place - geometry, reachability from the hero's start,
    every speaker still on walkable ground. Two tries; then None, and
    the caller keeps the scaffold's proven layout.
    """
    town = w["town"]
    legend = town["legend"]
    rows_n = len(town["map"])
    cols = len(town["map"][0])
    hero = town["hero_start"]
    speakers = ", ".join(f"{s['name']} at {tuple(s['at'])}" for s in w["speakers"].values())
    pois = "; ".join(f"{town['pois'][k]} at ({k})" for k in town.get("pois", {}))
    legend_text = "; ".join(
        f"'{ch}': "
        + (
            "solid"
            if e.get("solid") is True
            else "walkable"
            if e.get("solid") is False
            else "context"
        )
        for ch, e in sorted(legend.items())
    )
    prompt = (
        f"The story: {story or 'unspecified'}. The town should feel: {mood}.\n"
        f"Grid: exactly {rows_n} rows of width {cols}. Legend: {legend_text}.\n"
        f"The hero starts at {tuple(hero)}. Speakers stand at: {speakers or 'none'}. "
        f"Points of interest: {pois or 'none'}. "
        f"The current map:\n" + "\n".join(town["map"]) + "\n"
        f"Draw the town anew: same {rows_n} rows of width {cols}, legend "
        f"characters only, walkable paths from the hero's start reaching "
        f"every speaker, every point of interest, and every door. Keep at "
        f"least one safe place. Reply with only the JSON object: rows."
    )
    payload = {
        "model": generator.MODEL,
        "system": MAP_SYSTEM,
        "prompt": prompt,
        "format": _map_schema(legend),
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.8},
    }
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            rows = maplab.build_map(MapRows.model_validate_json(raw).to_segments())
            if len(rows) != rows_n or len(rows[0]) != cols:
                continue
            if any(ch not in legend for ch in set("".join(rows))):
                continue
            candidate = {**copy.deepcopy(w), "town": {**town, "map": rows}}
            # Geometry gate only: no pack_dir, so on-disk voice-file
            # checks stay out of it - the interview's final validate
            # (pack_dir=dest) is the full gate before anything ships.
            if not maplab.validate(candidate):
                return rows
        except (httpx.HTTPError, generator.GeneratorUnavailable,
                generator.GeneratorFailed,
                ValidationError, KeyError, ValueError, SystemExit):
            continue
    return None


FACE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "role": {"type": "string"},
        "seed": {"type": "string"},
    },
    "required": ["name", "role", "seed"],
}

FACE_SYSTEM = (
    "You propose one person who could live in this world. Keep them "
    "quiet and specific. Name, role, and one short line of seed "
    "dialogue they might say to someone passing by. Reply with only "
    "the JSON object: name, role, seed."
)


class Face(BaseModel):
    name: str
    role: str
    seed: str


def propose_face(story: str, mood: str, w: dict) -> dict | None:
    """One new face: name, role and a seed line, schema-constrained.

    Placement is never the model's choice - the caller asks _pick_tile
    for a reachable, unoccupied, non-flooded spot. Returns None on any
    failure so the caller keeps its honest fallback.
    """
    legend_text = "; ".join(
        f"'{ch}': "
        + (
            "solid"
            if e.get("solid") is True
            else "walkable"
            if e.get("solid") is False
            else "context"
        )
        for ch, e in sorted(w["town"].get("legend", {}).items())
    )
    payload = {
        "model": generator.MODEL,
        "system": FACE_SYSTEM,
        "prompt": (
            f"The story: {story or 'unspecified'}. The town should feel: {mood}.\n"
            f"The ground is marked: {legend_text or 'nothing named yet'}.\n"
            "Propose one person who belongs here."
        ),
        "format": FACE_SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": generator.KEEP_ALIVE,
        "options": {"temperature": 0.8},
    }
    for _ in range(2):
        try:
            raw = generator._completion(payload)
            face = Face.model_validate_json(raw)
            if face.name.strip() and face.role.strip() and face.seed.strip():
                return face.model_dump()
        except (httpx.HTTPError, generator.GeneratorUnavailable,
                generator.GeneratorFailed,
                ValidationError, KeyError, ValueError, SystemExit):
            continue
    return None


def _pick_tile(w: dict) -> tuple[int, int] | None:
    """Where a new townsperson stands, chosen by deterministic code.

    Reachable from the hero's start, not on anyone's spot, not on
    flood ground, and as far from the existing crowd as the town
    allows - the closest tile at the widest spread band. None when
    the town has no room left.
    """
    town = w["town"]
    start = tuple(town["hero_start"])
    flooded = {tuple(t) for t in town.get("flood_tiles", [])}
    seen = sorted(maplab.reach(w, start, flooded=flooded or None))
    taken = {start} | {tuple(s["at"]) for s in w["speakers"].values()}

    def spread(t: tuple) -> int:
        return min(abs(t[0] - a) + abs(t[1] - b) for a, b in taken)

    for want in (3, 2, 1):
        best = [t for t in seen if t not in taken and t not in flooded and spread(t) >= want]
        if best:
            return min(best, key=lambda t: (spread(t), t))
    return None


def _add_speaker(w: dict, dest: Path, name: str, personality: str) -> bool:
    """One new town voice: deterministic tile, drafted words.

    Returns False (and touches nothing) when the town has no free,
    reachable tile for them.
    """
    tile = _pick_tile(w)
    if tile is None:
        return False
    key = slugify(name)
    n = 2
    while key in w["speakers"]:
        key = f"{slugify(name)}-{n}"
        n += 1
    near = draft(
        f"{name} is: {personality}. Where do they stand in a small town? "
        f"One short phrase, 2-4 words, like 'the gate' or 'the low wall'.",
        system="You write tiny place descriptions. Two to four words.",
    )
    spec = {
        "name": name,
        "at": [tile[0], tile[1]],
        "near": near or "nearby",
        "voice_file": f"voices/{key}.md",
        "seeds": {},
    }
    for phase_key in w["phases"]:
        spec["seeds"][phase_key] = draft(
            f"{name} is: {personality}. It's the '{phase_key}' phase. Write "
            f"one short line they might say, unprompted, to someone passing by.",
            system=(
                "You write one short spoken line for an NPC, "
                "in-character, no quotation marks, no attribution."
            ),
        )
    voice_text = draft(
        f"{name} is: {personality}. Write 3-5 short bullet rules for how "
        f"they speak and what they know.",
        system=(
            "You write a short voice-and-rules file for an NPC: how "
            "they talk, what they know, what they never say. Plain "
            "markdown, no heading."
        ),
    )
    voices_dir = dest / "voices"
    voices_dir.mkdir(exist_ok=True)
    (voices_dir / f"{key}.md").write_text(f"# {name}\n\n{voice_text}\n", encoding="utf-8")
    w["speakers"][key] = spec
    return True


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    reply = input(f"{prompt}{suffix}\n> ").strip()
    return reply or default


def slugify(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "my-world"


def _rename_phase_keys(w: dict, old: list[str], new: list[str]) -> None:
    """Rename phase keys everywhere the pack contract references them:
    phases, water_by_phase, watch.r_by_phase, every speaker's seeds."""
    mapping = dict(zip(old, new))
    w["phases"] = {mapping.get(k, k): v for k, v in w["phases"].items()}
    town = w.get("town", {})
    if "water_by_phase" in town:
        town["water_by_phase"] = {mapping.get(k, k): v for k, v in town["water_by_phase"].items()}
    r_by_phase = town.get("watch", {}).get("r_by_phase")
    if r_by_phase:
        town["watch"]["r_by_phase"] = {mapping.get(k, k): v for k, v in r_by_phase.items()}
    for spec in w.get("speakers", {}).values():
        if "seeds" in spec:
            spec["seeds"] = {mapping.get(k, k): v for k, v in spec["seeds"].items()}


def run_interview(dest: Path, scaffold: Path) -> int:
    if dest.exists():
        print(f"a world already lives at {dest} - pick a new name or remove it first")
        return 1

    shutil.copytree(scaffold, dest)
    # The new pack keeps the scaffold's shape (flat or acts).
    # If the scaffold is acts-shape, the copy inherits acts/ and
    # the loader reads it as such; if flat, no acts/ exists and
    # the loader reads the flat JSON. Either way, maplab.load_pack
    # returns a unified shape the interview can mutate.
    from .maplab import load_pack as _load_pack

    w = _load_pack(dest)

    print("\nnorns chat - let's build your world.\n")
    title = ask("What's your world called?", w["title"])
    premise = ask("In one or two sentences, what's the story?")
    protagonist = ask("Who is your protagonist, in a few words?")

    w["title"] = title
    if premise:
        w["description"] = premise

    print("\ndrafting the canon (logbok.md)...")
    logbok_text = draft(
        f"The world is called {title}. The story: {premise or 'unspecified'}. "
        f"The protagonist: {protagonist or 'unspecified'}. Write a short "
        f"world logbok: the central truth of this place, and one or two "
        f"rules the story must never break. Plain prose, 4-8 sentences."
    )
    (dest / "logbok.md").write_text(f"# {title}\n\n{logbok_text}\n", encoding="utf-8")
    print(f"\n--- logbok.md ---\n{logbok_text}\n")

    theme_mood = ask(
        "In a few words, what's the color mood of your world? "
        "(e.g. 'candlelit church', 'cold moonlit fen') - blank keeps "
        "the scaffold's colors"
    )
    if theme_mood:
        colors = draft_theme(theme_mood)
        if colors:
            w["town"]["bg"] = colors["bg"]
            w["town"]["hero_color"] = colors["hero_color"]
            for entry in w["town"]["legend"].values():
                if "deco" in entry:
                    entry["deco_color"] = colors["deco_color"]
            print(
                f"  theme: bg {colors['bg']}, protagonist "
                f"{colors['hero_color']}, accent {colors['deco_color']}"
            )
        else:
            print("  theme draft failed twice - keeping the scaffold's colors")

    old_phases = list(w["phases"].keys())
    print(
        f"Your world has {len(old_phases)} phases (moods the town passes "
        f"through), currently named: {', '.join(old_phases)}."
    )
    new_names = ask(
        f"Rename them? Comma-separated, same count ({len(old_phases)}), or leave blank to keep"
    )
    if new_names:
        names = [n.strip() for n in new_names.split(",")]
        if len(names) == len(old_phases):
            _rename_phase_keys(w, old_phases, names)
        else:
            print(f"needed {len(old_phases)} names, got {len(names)} - keeping the originals")

    for key in list(w["phases"].keys()):
        tone_hint = ask(f"In a few words, what's the mood of '{key}'?")
        if tone_hint:
            w["phases"][key] = draft(
                f"The phase is called '{key}'. The author describes its "
                f"mood as: {tone_hint}. Write one sentence.",
                system=(
                    "You write one-sentence mood descriptions for a game's "
                    "time-of-day phases. Plain, evocative, one sentence."
                ),
            )

    old_bonds = list(w["bonds"].keys())
    print(
        f"\nYour world has {len(old_bonds)} kinds of bond (how items "
        f"connect to your protagonist): {', '.join(old_bonds)}."
    )
    new_bond_names = ask(
        f"Rename them? Comma-separated, same count ({len(old_bonds)}), or leave blank to keep"
    )
    if new_bond_names:
        names = [n.strip() for n in new_bond_names.split(",")]
        if len(names) == len(old_bonds):
            w["bonds"] = {names[i]: w["bonds"][old_bonds[i]] for i in range(len(old_bonds))}
            old_bonds = names
        else:
            print(f"needed {len(old_bonds)} names, got {len(names)} - keeping the originals")

    for key in old_bonds:
        flavor = ask(f"In a few words, what does a '{key}' bond feel like?")
        if flavor:
            card = draft(
                f"The bond is called '{key}'. The author describes it as: "
                f"{flavor}. Write one short clause, under 8 words, no "
                f"period needed.",
                system="You write short flavor text for an item's bond.",
            )
            prompt_text = draft(
                f"The bond is called '{key}'. The author describes it as: "
                f"{flavor}. Write one sentence a story-generator can use "
                f"to shape that bond's items.",
                system=(
                    "You write one sentence describing how an item with "
                    "this bond behaves in a story, for a prompt an AI will "
                    "read."
                ),
            )
            w["bonds"][key] = {"card": card, "prompt": prompt_text}

    map_mood = ask(
        "In a few words, how should the town feel to walk? "
        "(e.g. 'tight lanes around a well') - blank keeps the "
        "scaffold's proven layout"
    )
    if map_mood:
        print("\nthe model is drawing your town...")
        rows = propose_map(premise or title, map_mood, w, dest)
        if rows:
            w["town"]["map"] = rows
            print(f"  the map grew from your answer: {len(rows)} x {len(rows[0])}, validated.")
        else:
            print(
                "  the map draft never validated twice - keeping the "
                "scaffold's proven layout (always try: norns validate "
                f"--pack {dest})"
            )

    speaker_count_raw = ask("\nHow many people stand in your town? (1-3, blank = 1)", "1")
    try:
        speaker_count = max(1, min(3, int(speaker_count_raw)))
    except ValueError:
        print("  1-3 people - keeping one for now")
        speaker_count = 1

    speaker_key = next(iter(w["speakers"]))
    spec = w["speakers"][speaker_key]
    new_speaker_name = ask(
        f"Your first townsperson is '{spec['name']}'. What should they be called?",
        spec["name"],
    )
    personality = ask(f"In a few words, who is {new_speaker_name}?")
    spec["name"] = new_speaker_name
    if personality:
        for phase_key in w["phases"]:
            spec.setdefault("seeds", {})[phase_key] = draft(
                f"{new_speaker_name} is: {personality}. It's the "
                f"'{phase_key}' phase. Write one short line they might say, "
                f"unprompted, to someone passing by.",
                system=(
                    "You write one short spoken line for an NPC, "
                    "in-character, no quotation marks, no attribution."
                ),
            )
        voice_text = draft(
            f"{new_speaker_name} is: {personality}. Write 3-5 short bullet "
            f"rules for how they speak and what they know.",
            system=(
                "You write a short voice-and-rules file for an NPC: how "
                "they talk, what they know, what they never say. Plain "
                "markdown, no heading."
            ),
        )
        (dest / spec["voice_file"]).write_text(
            f"# {new_speaker_name}\n\n{voice_text}\n", encoding="utf-8"
        )

    for i in range(speaker_count - 1):
        sp_name = ask(f"Who else stands there? ({i + 2} of {speaker_count}) - blank stops here")
        if not sp_name:
            break
        sp_personality = ask(f"In a few words, who is {sp_name}?")
        if _add_speaker(w, dest, sp_name, sp_personality):
            print(f"  {sp_name} takes a spot on the map.")
        else:
            print("  no walkable, reachable tile left for them - the town stays as it is")
            break

    maplab.write_pack(dest, w)

    print("\nchecking your world...")
    errors = maplab.validate(w, pack_dir=dest)
    if errors:
        print(
            f"\n{len(errors)} problem(s) found - the map/geometry from the "
            f"scaffold shouldn't be able to break, so this is worth a look:"
        )
        for e in errors:
            print(f"  FAIL: {e}")
        print(f"\nFix by hand in {dest}, then: norns validate --pack {dest}")
        return 1

    print(f"\nok - {dest} is valid and ready.")
    print("\nNext steps:")
    print(f"  VEFR_WORLD={dest.name} norns validate --pack {dest}")
    print(f"  VEFR_WORLD={dest.name} ratatoskr test")
    print(f"  reshape the map later with: norns build-map --segments <file> --pack {dest}")
    return 0
