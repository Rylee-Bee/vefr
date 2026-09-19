"""Prompt building helpers.

Every task retains its exact final message list in the trial record; these
builders just make the common structured cases consistent (and therefore
comparable across contestants).

Tool-call protocol taught in prompts (single dialect; parser accepts many):
  <|tool_call|> {"name": "...", "arguments": {...}} <|/tool_call|>
"""

from .tools import render_tools, CALL, CALL_END

TOOL_SYSTEM_BASE = (
    "You are a bounded assistant with access to tools.\n"
    "Rules:\n"
    "1. Call a tool ONLY when you need information you do not already have.\n"
    "2. If you already have what you need, or no tool applies, answer directly in plain text.\n"
    "3. Never invent tools. Use only the tools listed.\n"
    "4. When a tool is required, reply with exactly one call line:\n"
    f'    {CALL} {{"name": "tool_name", "arguments": {{...}}}} {CALL_END}\n'
    "    No prose around the call.\n"
)

JSON_SYSTEM_BASE = (
    "Reply with ONLY valid JSON. No markdown fences, no prose. "
    "Follow the requested schema exactly."
)

PROSE_SYSTEM_BASE = (
    "Reply in plain prose. Do not use JSON or tool-call syntax."
)


def tool_system(tools=None, notes=None, base=TOOL_SYSTEM_BASE):
    parts = [base]
    if tools:
        parts.append("Available tools:\n" + render_tools(tools))
    if notes:
        parts.append("Additional instructions:\n" + "\n".join("- " + n for n in notes))
    return "\n".join(parts)


def json_system(notes=None):
    parts = [JSON_SYSTEM_BASE]
    if notes:
        parts.append("\n".join("- " + n for n in notes))
    return "\n".join(parts)


def prose_system(notes=None):
    parts = [PROSE_SYSTEM_BASE]
    if notes:
        parts.append("\n".join("- " + n for n in notes))
    return "\n".join(parts)


def msgs(system, user):
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# --------------------------------------------------------------------------
# Agentic Compression - the GUIDED layer. A small, portable, engine-neutral
# guide appended to the system prompt. SCAFFOLDED adds schemas/validators
# (already part of the rig's task definitions). We measure RAW vs GUIDED with
# identical tasks otherwise.
# --------------------------------------------------------------------------
GUIDE = (
    "The bounded-work guide:\n"
    "- Reply with only what was asked. No preamble, no postscript.\n"
    "- If a fact is not supplied or not known, write UNKNOWN instead of "
    "guessing.\n"
    "- Acknowledgment is not verification; acceptance is not authorization.\n"
    "- The newest authoritative source beats older observations.\n"
    "- Sources you are given outrank remembered background knowledge.\n"
    "- When in doubt about the task, reason silently then answer plainly.\n"
)


def guide_tasks(tasks):
    """Return tasks with the GUIDE prepended to their system/first session
    system. Tasks are shallow-copied so raw evidence remains untouched."""
    import copy
    out = []
    for t in tasks:
        t2 = copy.deepcopy(t)
        if t2.get("system"):
            t2["system"] = GUIDE + "\n" + t2["system"]
        elif t2.get("session") and t2["session"][0].get("system"):
            t2["session"][0]["system"] = GUIDE + "\n" + t2["session"][0]["system"]
        else:
            t2["system"] = GUIDE
            t2.pop("user", None)
        out.append(t2)
    return out