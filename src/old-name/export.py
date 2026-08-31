"""The export - the world's tree, woven from the dev UI's tabs.

Named for Yggdrasil: the Norns weave fate at the well beneath the
world tree, and what we weave here is the same kind of thing - the
player's story, growing from the canon at the roots up into the
branches of what actually happened. The Norns don't weave one fixed
fate; whichever story the player gives them.

Deliberately deterministic templating, not another model pass: the
export has to work when ollama is cold, and it has to match the
journal exactly. A model-polish pass over this output is a natural
second step; it is not this step.

Two shapes:

  export_story()       the full World Tree - one section per
                       dev-UI tab, in the order the player met them.
                       This is what `old-name build` writes alongside
                       the playable HTML file as <name>.tree.md.

  export_tab(name)     one section per individual tab - what the
                       "Export this tab" button in the web UI calls.

The six tabs map to six section headings (with the canon as a
preface before any of them):

  ## The Fen Walked    moves + sightings the journal can witness
  ## The Whispers Heard  the rumors the player actually clicked
  ## What Was Carried   the items they kept (named, bonded, lore)
  ## The Bell's Letters  every letter the bell gave, in order
  ## The Voices Heard   the lines NPCs spoke when the wanderer spoke to them
  ## The Journal        the rest, in pure chronological order (anything
                       the per-tab sections did not cover)

Empty journal + empty vault is a valid playthrough - a world nobody
has played yet - and produces a shorter document, not an error.
"""

import json

from .forge import list_vault
from .journal import list_entries
from .saga import bible
from .world import load_world


# ---- shared helpers ----

def _para(text) -> str:
    """One line, no stray whitespace - markdown-safe prose."""
    return " ".join(str(text).split())


def _demote(canon: str, demote: int = 1) -> str:
    """Shift the bible's headings down by `demote` levels.

    The document already has at least one H1 - the world's title -
    and "## The World Tree" sits between them. So the pack's own
    `# ...` heading becomes `### ...` (demote=2), nesting under the
    tree, and the pack's `## ...` becomes `#### ...`. Fenced code is
    left alone; a `#` inside a fence is not a heading.
    """
    out: list[str] = []
    fenced = False
    for line in canon.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            depth = len(line) - len(line.lstrip("#"))
            if depth < 6:
                line = ("#" * demote) + line
        out.append(line)
    return "\n".join(out)


# ---- per-kind renderers (unchanged) ----

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


# ---- the title + canon preface (shared by every shape) ----

def _preface(world: dict, name: str | None = None) -> list[str]:
    """The H1 world title and the demoted bible.md canon.

    Every export starts with these - they're the world's identity,
    not its play history. The per-tab sections follow. The canon
    sits under '## The World Tree' (Yggdrasil) so the reader knows
    the roots-of-the-story are loaded first.
    """
    parts: list[str] = [f"# {world['title']}"]
    canon = bible(name).strip()
    if canon:
        parts.append("## The World Tree")
        # The bible's own heading is nested under "The World Tree";
        # keep the bible's structure but shift its H1 down to H3.
        parts.append(_demote(canon, demote=2))
    return parts


# ---- per-tab section builders ----
#
# Each builder is given the journal and returns a markdown string for
# its tab (or "" when there are no entries for this tab). The
# chronology of a tab is the order entries were journaled in - the
# dev UI tab renders them in that order, so the export should match.

def _rumors_section(entries: list[dict]) -> str:
    """The Rumors tab: only `kind: rumor` entries, in request order."""
    rumors = [e for e in entries if e.get("kind") == "rumor"]
    if not rumors:
        return ""
    lines = ["## The Whispers Heard"]
    for e in rumors:
        when = e.get("at", "?")[:19]
        phase = e.get("phase", "?")
        lines.append(f"- **{when}** ({phase}) {_entry(e)}")
    return "\n".join(lines)


def _vault_section(items: list[dict]) -> str:
    """The Vault tab: kept items, with phase + bond metadata."""
    if not items:
        return ""
    lines = ["## What Was Carried", ""]
    for item in items:
        name = _para(item.get("name") or "something without a name")
        bond = _para(item.get("bond") or "")
        lore = _para(item.get("lore") or "")
        enchant = _para(item.get("enchant") or "")
        curse = _para(item.get("curse") or "")
        head = f"### {name}"
        if bond:
            head += f" *({bond})*"
        lines.append(head)
        if lore:
            lines.append(f"_{lore}_")
        if enchant:
            lines.append(f"- enchant: {enchant}")
        if curse:
            lines.append(f"- curse: {curse}")
    return "\n".join(lines)


def _bell_section(entries: list[dict]) -> str:
    """The Bell tab: every letter, in order."""
    letters = [e for e in entries if e.get("kind") == "bell_letter"]
    if not letters:
        return ""
    lines = ["## The Bell's Letters", ""]
    for i, e in enumerate(letters, 1):
        when = e.get("at", "?")[:19]
        lines.append(f"### Letter {i} - {when}")
        lines.append("")
        lines.append(_entry(e))
        lines.append("")
    return "\n".join(lines).rstrip()


def _voices_section(entries: list[dict]) -> str:
    """The Voices (NPCs) tab: every npc_line, grouped by speaker."""
    lines_list = [e for e in entries if e.get("kind") == "npc_line"]
    if not lines_list:
        return ""
    by_speaker: dict[str, list[dict]] = {}
    for e in lines_list:
        by_speaker.setdefault(e.get("speaker") or "a voice", []).append(e)
    lines = ["## The Voices Heard", ""]
    for speaker, evs in by_speaker.items():
        lines.append(f"### {speaker}")
        for e in evs:
            when = e.get("at", "?")[:19]
            phase = e.get("phase", "?")
            lines.append(f"- ({phase}, {when}) {_entry(e)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _town_section(entries: list[dict]) -> str:
    """The Town tab: moves + sightings the journal can witness.

    Today the engine doesn't journal town movement (a TODO from
    earlier sessions - the move log lives only in the town's
    transient state). What we CAN say: every npc_line has a phase
    and that phase's `water_by_phase` was in effect. A minimal
    faithful section is "the town was visited during these phases,
    and the NPCs the player spoke to were near these places".
    """
    npc_phases = [
        (e.get("phase"), e.get("speaker")) for e in entries
        if e.get("kind") == "npc_line" and e.get("phase")
    ]
    if not npc_phases:
        return ""
    phases_seen = []
    for ph, _ in npc_phases:
        if ph not in phases_seen:
            phases_seen.append(ph)
    lines = ["## The Fen Walked", ""]
    lines.append("The town was walked during these phases:")
    lines.append("")
    for ph in phases_seen:
        lines.append(f"- **{ph}**")
    npc_at_phase = {}
    for ph, sp in npc_phases:
        npc_at_phase.setdefault(ph, set()).add(sp)
    if any(npc_at_phase.values()):
        lines.append("")
        lines.append("NPCs spoken to, by phase:")
        for ph, names in npc_at_phase.items():
            lines.append(f"- **{ph}**: {', '.join(sorted(names))}")
    return "\n".join(lines)


def _journal_section(entries: list[dict], exclude: set[str]) -> str:
    """The Journal tab: everything in pure chronological order,
    minus the entries the per-tab sections already covered."""
    rest = [e for e in entries if e.get("kind") not in exclude]
    if not rest:
        return ""
    lines = ["## The Journal", ""]
    for e in rest:
        when = e.get("at", "?")[:19]
        kind = e.get("kind", "?")
        lines.append(f"- **{when}** ({kind}) {_entry(e)}")
    return "\n".join(lines)


# ---- public API ----

# The kinds that have a dedicated tab section. Everything else goes
# into the catch-all "Journal" tab at the end.
_TAB_KINDS = {"rumor", "item_forged", "bell_letter", "npc_line"}


def export_story(world: str | None = None) -> str:
    """Weave canon + every tab into one readable markdown document.

    The shape:
      # World Title
      ## The World Tree - the demoted bible.md canon (the roots)
      ## The Fen Walked
      ## The Whispers Heard
      ## What Was Carried
      ## The Bell's Letters
      ## The Voices Heard
      ## The Journal    (anything the per-tab sections did not cover)
    """
    w = load_world(world)
    entries = list_entries()
    parts = _preface(w, name=world)

    town = _town_section(entries)
    if town:
        parts.append(town)

    rumors = _rumors_section(entries)
    if rumors:
        parts.append(rumors)

    vault = _vault_section(list_vault())
    if vault:
        parts.append(vault)

    bell = _bell_section(entries)
    if bell:
        parts.append(bell)

    voices = _voices_section(entries)
    if voices:
        parts.append(voices)

    journal = _journal_section(entries, _TAB_KINDS)
    if journal:
        parts.append(journal)

    if not any([
        _town_section(entries),
        _rumors_section(entries),
        _vault_section(list_vault()),
        _bell_section(entries),
        _voices_section(entries),
        _journal_section(entries, _TAB_KINDS),
    ]):
        parts.append("Nothing has happened here yet. The world is waiting.")

    return "\n\n".join(parts).rstrip() + "\n"


_TAB_NAMES = ("town", "rumors", "vault", "bell", "voices", "journal")


def export_tab(name: str, world: str | None = None) -> str:
    """One tab's worth of the world, as markdown.

    Returns the canon preface plus that one tab's section. Used by
    the per-tab "Export" buttons in the web UI.
    """
    if name not in _TAB_NAMES:
        raise ValueError(f"unknown tab {name!r}; expected one of {_TAB_NAMES}")
    w = load_world(world)
    entries = list_entries()
    parts = _preface(w, name=world)
    if name == "town":
        s = _town_section(entries)
    elif name == "rumors":
        s = _rumors_section(entries)
    elif name == "vault":
        s = _vault_section(list_vault())
    elif name == "bell":
        s = _bell_section(entries)
    elif name == "voices":
        s = _voices_section(entries)
    else:
        s = _journal_section(entries, _TAB_KINDS)
    if s:
        parts.append(s)
    else:
        parts.append(f"## {name.capitalize()}")
        parts.append("_Nothing yet._")
    return "\n\n".join(parts).rstrip() + "\n"