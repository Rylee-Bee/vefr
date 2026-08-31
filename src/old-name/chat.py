"""old-name chat - the conversational world-builder.

Copies worlds/sample-world/ as a known-good scaffold, then interviews
the author segment by segment (title, canon, theme colors, phases,
bonds, the one speaker) and drafts prose with the local model.

The conversation's *shape* is deterministic Python, never the model's
choice - which question comes next, whether a rename is structurally
safe, whether the pack validates. The model only ever fills in prose
inside a schema it cannot escape. Geometry (the map itself) is left
untouched in v1; grow it afterward with `old-name build --segments`.

Every write ends with maplab.validate() - the author never has to
trust their own edits, the tool always checks.
"""

import json
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
        "willow_color": {"type": "string"},
        "deco_color": {"type": "string"},
    },
    "required": ["bg", "willow_color", "deco_color"],
}

THEME_SYSTEM = (
    "You choose a color palette for a quiet, dark, migraine-safe game "
    "UI. Every color must be a 6-digit hex code. The background must "
    "stay dark and low-saturation (near-black, muted). The protagonist "
    "color must read clearly against that dark background. The accent "
    "color is a small warm highlight, never neon, never fully "
    "saturated. Reply with only the JSON object: bg, willow_color, "
    "deco_color."
)


class Theme(BaseModel):
    bg: str
    willow_color: str
    deco_color: str

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
        except (httpx.HTTPError, ValidationError, KeyError, ValueError):
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
            f"The mood is: {mood}. Reply with only the JSON object: "
            f"bg, willow_color, deco_color."
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
            if all(HEX_RE.match(v) for v in (colors.bg, colors.willow_color, colors.deco_color)):
                return colors.model_dump()
        except (httpx.HTTPError, ValidationError, KeyError, ValueError):
            continue
    return None


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
        town["water_by_phase"] = {
            mapping.get(k, k): v for k, v in town["water_by_phase"].items()
        }
    r_by_phase = town.get("watch", {}).get("r_by_phase")
    if r_by_phase:
        town["watch"]["r_by_phase"] = {
            mapping.get(k, k): v for k, v in r_by_phase.items()
        }
    for spec in w.get("speakers", {}).values():
        if "seeds" in spec:
            spec["seeds"] = {mapping.get(k, k): v for k, v in spec["seeds"].items()}


def run_interview(dest: Path, scaffold: Path) -> int:
    if dest.exists():
        print(f"a world already lives at {dest} - pick a new name or remove it first")
        return 1

    shutil.copytree(scaffold, dest)
    w = json.loads((dest / "world.json").read_text(encoding="utf-8"))

    print("\nsmidr chat - let's build your world.\n")
    title = ask("What's your world called?", w["title"])
    premise = ask("In one or two sentences, what's the story?")
    protagonist = ask("Who is your protagonist, in a few words?")

    w["title"] = title
    if premise:
        w["description"] = premise

    print("\ndrafting the canon (bible.md)...")
    bible_text = draft(
        f"The world is called {title}. The story: {premise or 'unspecified'}. "
        f"The protagonist: {protagonist or 'unspecified'}. Write a short "
        f"world bible: the central truth of this place, and one or two "
        f"rules the story must never break. Plain prose, 4-8 sentences."
    )
    (dest / "bible.md").write_text(f"# {title}\n\n{bible_text}\n", encoding="utf-8")
    print(f"\n--- bible.md ---\n{bible_text}\n")

    theme_mood = ask(
        "In a few words, what's the color mood of your world? "
        "(e.g. 'candlelit church', 'cold moonlit fen') - blank keeps "
        "the scaffold's colors"
    )
    if theme_mood:
        colors = draft_theme(theme_mood)
        if colors:
            w["town"]["bg"] = colors["bg"]
            w["town"]["willow_color"] = colors["willow_color"]
            for entry in w["town"]["legend"].values():
                if "deco" in entry:
                    entry["deco_color"] = colors["deco_color"]
            print(
                f"  theme: bg {colors['bg']}, protagonist "
                f"{colors['willow_color']}, accent {colors['deco_color']}"
            )
        else:
            print("  theme draft failed twice - keeping the scaffold's colors")

    old_phases = list(w["phases"].keys())
    print(
        f"Your world has {len(old_phases)} phases (moods the town passes "
        f"through), currently named: {', '.join(old_phases)}."
    )
    new_names = ask(
        f"Rename them? Comma-separated, same count ({len(old_phases)}), or "
        f"leave blank to keep"
    )
    if new_names:
        names = [n.strip() for n in new_names.split(",")]
        if len(names) == len(old_phases):
            _rename_phase_keys(w, old_phases, names)
        else:
            print(
                f"needed {len(old_phases)} names, got {len(names)} - "
                f"keeping the originals"
            )

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
        f"Rename them? Comma-separated, same count ({len(old_bonds)}), or "
        f"leave blank to keep"
    )
    if new_bond_names:
        names = [n.strip() for n in new_bond_names.split(",")]
        if len(names) == len(old_bonds):
            w["bonds"] = {names[i]: w["bonds"][old_bonds[i]] for i in range(len(old_bonds))}
            old_bonds = names
        else:
            print(
                f"needed {len(old_bonds)} names, got {len(names)} - "
                f"keeping the originals"
            )

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

    speaker_key = next(iter(w["speakers"]))
    spec = w["speakers"][speaker_key]
    new_speaker_name = ask(
        f"Your one town speaker is '{spec['name']}'. What should they be called?",
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
        print(f"\nFix by hand in {dest}, then: old-name validate --pack {dest}")
        return 1

    print(f"\nok - {dest} is valid and ready.")
    print("\nNext steps:")
    print(f"  NORN_WORLD={dest.name} old-name validate --pack {dest}")
    print(f"  NORN_WORLD={dest.name} raven test")
    print(
        "  grow the map with: old-name build --segments <file> --pack "
        f"{dest}"
    )
    return 0
