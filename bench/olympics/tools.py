"""Tool schema helpers + canonical renderings.

We prompt-render tools (BFCL #861 lesson: native API fields are a harness
choice, not a model capability). The rig accepts MANY output dialects; this
module only renders input. Parsing lives in parse.py.
"""

import json

# canonical tool-call marker we teach in prompts
CALL = "<|tool_call|>"
CALL_END = "<|/tool_call|>"


def render_tools(tools):
    """Render a tool shelf for the prompt. tools: list of dicts."""
    if not tools:
        return ""
    return "<tools>\n" + json.dumps(tools) + "\n</tools>"


def no_tools_block(already_known=None, forbidden=None):
    lines = []
    lines.append("Available tools:\n<tools>\n[]\n</tools>")
    return "\n".join(lines)


def restriction_block(notes):
    """Extra rules for tool-judgment tests (already have info, NOT etc.)."""
    return "\n".join(notes)


def schema_of(tools, names=None):
    names = set(names or [t["name"] for t in tools])
    return {t["name"]: t for t in tools if t["name"] in names}