"""The visible engine - three endpoints that let the author see
exactly what the loader did, what the engine sees, and package
the whole context for an AI-buddy debugging handoff.

  GET  /api/weave               the weave log (recent events)
  GET  /api/weave/resolved      the merged world the engine sees
                                after convention resolution
  POST /api/handoff             write a markdown bundle to disk,
                                ready to paste into a chat with
                                an AI buddy or a junior dev

These are dev-only: the packaged game has none of them. The
endpoints are honest mirrors of the loader's internals; the
template format is the same on disk and in the bundle.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from . import weave as weave_mod
from .paths import app_home
from .world import load_world


def recent_weave(limit: int = 200) -> dict:
    """Return the in-memory ring of weave events, newest first."""
    return {"events": weave_mod.recent(limit)}


def resolved_world() -> dict:
    """The merged world dict after convention resolution - the actual
    data the engine is using, not the on-disk files. Includes the
    journey anchors, the resolved act's regions, and the loader's
    bookkeeping. Pretty-printed for the handoff bundle.
    """
    w = load_world()
    # Strip keys that are pure engine metadata and not useful
    # in the resolved view (cache markers, etc.).
    return {
        "name": w["name"],
        "title": w["title"],
        "description": w.get("description", ""),
        "gold_rule": w.get("gold_rule", ""),
        "surface": w["surface"],
        "phases": w["phases"],
        "bonds": w.get("bonds", {}),
        "voices": w.get("voices", {}),
        "acts": [
            {
                "id": a["id"],
                "title": a["title"],
                "regions": list(a["regions"].keys()),
                "speakers": a["speakers"],
                "enemies": a.get("enemies", []),
                "bosses": a.get("bosses", []),
                "transitions": a.get("transitions", []),
                "vault_intro": a.get("vault_intro", ""),
                "verbs": a.get("verbs", []),
            }
            for a in w["acts"]
        ],
        "_current_act": w["_current_act"],
        "_shape": w["_shape"],
    }


def build_handoff(out_dir: Path | None = None) -> Path:
    """Write a markdown bundle to disk. Returns the path.

    The bundle has three sections:

      # Context        the resolved world + recent weave events
      # What I tried   the author's free-text description
      # What happened  the runtime error / symptom / observation

    The first two are auto-filled; the third is a template the
    author fills in before sharing. See docs/guides/handoff.md.
    """
    out_dir = out_dir or app_home() / "data" / "handoffs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"handoff-{stamp}.md"

    resolved = resolved_world()
    weave_events = weave_mod.recent(50)

    parts: list[str] = []
    parts.append("# Handoff bundle")
    parts.append("")
    parts.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    parts.append(f"Engine pack: `{resolved['name']}` (shape: `{resolved['_shape']}`, "
                 f"surface: `{resolved['surface']}`)")
    parts.append("")
    parts.append("## What I was trying to do")
    parts.append("")
    parts.append("_(fill this in: what were you doing when it went sideways? "
                 "what did you expect to happen?)_")
    parts.append("")
    parts.append("## What I saw instead")
    parts.append("")
    parts.append("_(fill this in: error message, the thing that surprised you, "
                 "the symptom you can reproduce)_")
    parts.append("")
    parts.append("## What I've already tried")
    parts.append("")
    parts.append("_(bullet list is fine - what you did, even if it didn't work)_")
    parts.append("")
    parts.append("## Context for the buddy")
    parts.append("")
    parts.append("### The resolved world (what the engine sees)")
    parts.append("")
    parts.append("```json")
    parts.append(json.dumps(resolved, indent=2, ensure_ascii=False))
    parts.append("```")
    parts.append("")
    parts.append("### Recent weave events (newest first)")
    parts.append("")
    if weave_events:
        parts.append("```json")
        parts.append(json.dumps(weave_events[:50], indent=2, ensure_ascii=False))
        parts.append("```")
    else:
        parts.append("_(no weave events yet - run the engine once to populate)_")
    parts.append("")
    parts.append("## The task")
    parts.append("")
    parts.append("You are an AI debugging buddy for the vefr engine. The author "
                 "above is stuck on something. The world JSON and the recent "
                 "engine events are inlined. Read them, then:")
    parts.append("")
    parts.append("1. State the most likely cause in one sentence.")
    parts.append("2. Suggest the smallest change that would unblock them.")
    parts.append("3. If the cause is in the world's own data, point at the "
                 "specific key.")
    parts.append("4. If the cause is in the engine's loader, name the function "
                 "and the line where the wiring should change.")
    parts.append("")
    parts.append("Do not rewrite large chunks. The author wants a single "
                 "concrete next step, not a refactor.")
    parts.append("")

    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def _ensure_data_dir() -> None:
    """The handoff directory may be on a read-only mount in some
    installs; surface a clean error rather than an OSError trace."""
    target = app_home() / "data" / "handoffs"
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"cannot create handoff directory at {target}: {e}"
        )
