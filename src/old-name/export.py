"""The export - canon plus what actually happened, as one document.

Deliberately deterministic templating, not another model pass: the
export has to work when ollama is cold, and it has to match the
journal exactly. A model-polish pass over this output is a natural
second step; it is not this step.

Reads three sources, none of which it owns:
  - the world pack's title and bible.md (the canon)
  - the journal (what happened, in order)
  - the vault (what was carried out)

An empty journal and an empty vault are a valid playthrough - a
world nobody has played yet - and produce a shorter document, not
an error.
"""

import json

from .forge import list_vault
from .journal import list_entries
from .saga import bible
from .world import load_world


def _para(text) -> str:
    """One line, no stray whitespace - markdown-safe prose."""
    return " ".join(str(text).split())


def _demote(canon: str) -> str:
    """Shift the bible's headings down one level.

    The document already has exactly one H1 - the world's title - so
    the pack's own `# ...` heading becomes `## ...` and nests under it.
    Fenced code is left alone; a `#` inside a fence is not a heading.
    """
    out: list[str] = []
    fenced = False
    for line in canon.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            depth = len(line) - len(line.lstrip("#"))
            if depth < 6:
                line = "#" + line
        out.append(line)
    return "\n".join(out)


def _rumor(e: dict) -> str:
    speaker = _para(e.get("speaker") or "someone with no name left")
    line = f"{speaker} whispered: \u201c{_para(e.get('whisper') or '')}\u201d"
    if e.get("is_true") is False:
        line += " It was not true, or not true yet."
    return line


def _npc_line(e: dict) -> str:
    speaker = _para(e.get("speaker") or "a voice")
    return f"{speaker} said: \u201c{_para(e.get('line') or '')}\u201d"


def _item_forged(e: dict) -> str:
    name = _para(e.get("name") or "something without a name")
    bond = _para(e.get("bond") or "")
    lore = _para(e.get("lore") or "")
    line = f"{name} came to hand"
    if bond:
        line += f" \u2014 {bond}"
    line += "."
    if lore:
        line += f" {lore}"
    return line


def _bell_letter(e: dict) -> str:
    letter = str(e.get("letter") or "").strip()
    if not letter:
        return "> A letter was found, and said nothing."
    return "\n".join(
        ("> " + ln if ln.strip() else ">") for ln in letter.splitlines()
    )


_RENDER = {
    "rumor": _rumor,
    "npc_line": _npc_line,
    "item_forged": _item_forged,
    "bell_letter": _bell_letter,
}


def _entry(e: dict) -> str:
    render = _RENDER.get(e.get("kind", ""))
    if render is None:
        # An unknown kind is forward-compatible data, not a crash: keep
        # it verbatim so a newer journal still exports readably.
        return _para(json.dumps(e, ensure_ascii=False))
    return render(e)


def _carried(items: list[dict]) -> str:
    lines = []
    for item in items:
        name = _para(item.get("name") or "something without a name")
        bond = _para(item.get("bond") or "")
        lore = _para(item.get("lore") or "")
        head = f"- **{name}**" + (f" ({bond})" if bond else "")
        lines.append(head + (f" \u2014 {lore}" if lore else ""))
    return "\n".join(lines)


def export_story(world: str | None = None) -> str:
    """Weave canon, journal, and vault into one readable markdown doc."""
    w = load_world(world)
    parts: list[str] = [f"# {w['title']}"]

    canon = bible(world).strip()
    if canon:
        parts.append(_demote(canon))

    entries = list_entries()
    parts.append("## What happened")
    if entries:
        parts.extend(_entry(e) for e in entries)
    else:
        parts.append("Nothing has happened here yet. The world is waiting.")

    kept = list_vault()
    if kept:
        parts.append("## What was carried")
        parts.append(_carried(kept))

    return "\n\n".join(parts).rstrip() + "\n"
