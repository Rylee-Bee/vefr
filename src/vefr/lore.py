"""Lore packs - the wandering-poets shape.

A lore pack is a directory under worlds/lore/<name>/ with four
markdown files the engine reads and a fifth the author copies by
hand:

  textures.md    the mood-board prose (engine reads)
  names.md       the word-hoard (engine reads)
  questions.md   the wandering questions (engine reads)
  prompt.md      the copy-paste prompt for any LLM (author reads)
  LICENSE.md     the licensing terms (CC BY-SA 4.0 + sources)

The lore pack is data, not code. Adding a new flavor is `mkdir
worlds/lore/<name>` and writing the four files - no PR to the
engine. The engine reads them; the author copies the prompt.

A lore pack does NOT decide the world. It seeds the world's
mood. The actual canon (world.json, logbok.md, voices/, map)
is shaped by norns chat, with the lore pack's textures
woven into the system prompt. The lore is what the world feels
like; the chat is what the world becomes.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class LorePreviewRequest(BaseModel):
    lore: str  # pack name under worlds/lore/<lore>/
    seeds: list[str] = []
    mood: Optional[str] = None


class LorePreviewResponse(BaseModel):
    """The wandering-poets shape: mood, names, questions. No canonical fields.

    Lore is not a canon. It is a mood-board. The author uses
    `textures` as the seed-prose they react to, `names` as
    vocabulary they might keep or change, and `questions` as
    the wandering questions they want the world to keep asking.
    """
    lore: str
    textures: str       # 2-4 paragraph prose, mood-board
    names: list[str]    # 5-10 suggested names
    questions: list[str]  # 2-4 wandering questions


class LoreListEntry(BaseModel):
    name: str
    title: str
    has_textures: bool
    has_names: bool
    has_questions: bool
    has_prompt: bool
    has_license: bool


# Where lore packs live. The engine repo's worlds/lore/ is the
# canonical registry; pack authors can add their own packs there
# (in a PR) or under their own story repo's worlds/lore/ (if
# they've forked the bones).
def _lore_root() -> Path:
    from .paths import app_home
    return app_home() / "worlds" / "lore"


def list_lore() -> list[LoreListEntry]:
    """Every lore pack under worlds/lore/, with a manifest of what it has."""
    root = _lore_root()
    if not root.exists():
        return []
    out: list[LoreListEntry] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        out.append(LoreListEntry(
            name=name,
            title=name.replace('-', ' ').replace('_', ' '),
            has_textures=(p / "textures.md").exists(),
            has_names=(p / "names.md").exists(),
            has_questions=(p / "questions.md").exists(),
            has_prompt=(p / "prompt.md").exists(),
            has_license=(p / "LICENSE.md").exists(),
        ))
    return out


def _read_pack_file(name: str, filename: str, req: LorePreviewRequest) -> str:
    """Read a lore pack file; fail helpfully if missing."""
    from .paths import app_home
    pack_dir = app_home() / "worlds" / "lore" / name
    path = pack_dir / filename
    if not path.exists():
        raise FileNotFoundError(
            f"lore pack '{name}' has no {filename} (looked at {path})"
        )
    return path.read_text(encoding="utf-8")


PREVIEW_SYSTEM = (
    "You are a wandering poet's first reader - an editor who "
    "weaves a mood-board into a single short passage. The lore "
    "pack below contains textures, names, and questions. You do "
    "NOT write a canon - you do NOT pick a title, name factions, "
    "or design a map. You write:\n"
    "  - textures: 2-4 paragraphs of mood-board prose that the "
    "    author can react to (not the world's canon - the world's *weather*)\n"
    "  - names: 5-10 suggested names drawn from the pack's word-hoard\n"
    "  - questions: 2-4 wandering questions the world keeps asking\n\n"
    "Show, don't explain. Roadside prose, not library prose. A "
    "little crooked over polished. The author will do the rest."
)


def _prompt(req: LorePreviewRequest, textures: str, names: str, questions: str) -> str:
    """Assemble the user-prompt half of the lore preview."""
    parts = [f"Lore pack: {req.lore}"]
    if req.mood:
        parts.append(f"Author's mood: {req.mood}")
    if req.seeds:
        parts.append(f"Author's seed words: {', '.join(req.seeds)}")
    parts.append(
        "\n=== textures.md ===\n" + textures[:6000] +
        "\n=== names.md ===\n" + names[:4000] +
        "\n=== questions.md ===\n" + questions[:4000]
    )
    parts.append(
        "\nWeave textures, names, and questions into the three "
        "output fields. Use the pack's vocabulary where it fits. "
        "Do not invent facts about the historical record or the "
        "rune poems - the pack is the source of truth."
    )
    return "\n".join(parts)


_PREVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "textures": {
            "type": "string",
            "description": "2-4 paragraphs of mood-board prose",
        },
        "names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "5-10 suggested names",
        },
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-4 wandering questions",
        },
    },
    "required": ["textures", "names", "questions"],
    "additionalProperties": False,
}


def preview_lore(req: LorePreviewRequest) -> LorePreviewResponse:
    """Read the lore pack files, send to the model, return the wandering shape.

    Reuses generator._completion (which now passes `messages`
    through unchanged when present). The lore pack's textures,
    names, and questions are the model's source of truth - we
    do not invent facts, we weave what the pack provides.
    """
    from . import generator as _gen

    textures = _read_pack_file(req.lore, "textures.md", req)
    names = _read_pack_file(req.lore, "names.md", req)
    questions = _read_pack_file(req.lore, "questions.md", req)

    payload = {
        "model": _gen.MODEL,
        "messages": [
            {"role": "system", "content": PREVIEW_SYSTEM},
            {"role": "user", "content": _prompt(req, textures, names, questions)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"schema": _PREVIEW_SCHEMA, "strict": True},
        },
        "max_tokens": 2048,
        "temperature": 0.95,
        "stream": False,
        "chat_template_kwargs": {"reasoning_effort": "low"},
    }
    import json as _json
    last_err = None
    for _ in range(2):
        try:
            raw = _gen._completion(payload)
            data = _json.loads(raw)
            return LorePreviewResponse(lore=req.lore, **data)
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(
        f"lore preview failed twice for pack {req.lore!r}: "
        f"{type(last_err).__name__}: {last_err}"
    )