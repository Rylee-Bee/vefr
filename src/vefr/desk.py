"""The Desk ruleset - verification and printing (Act 2).

Rumors arrive carrying a hidden truth value: the engine owns truth,
the model only proposes the whisper. The Desk lets a session judge
what it heard - verify a whisper as true or false - and the engine
compares the verdict against what it actually sent. Correct verdicts
become world knowledge (confirmed / debunked); printed headlines
become what the world has heard. Both feed back into every later
prompt, so the world knows its own stories and the NPCs speak from
them.

Knowledge is DERIVED from the session journal on every read - no
separate store to corrupt, migrate, or lose. Deterministic: no model
calls in this module (export-law surfaces stay model-free).
"""

from . import journal

VERDICTS = ("true", "false")


def _rumors(sid: str | None) -> list[dict]:
    return [e for e in journal.entries(sid) if e.get("kind") == "rumor"]


def _truth_of(sid: str | None, whisper: str) -> bool | None:
    heard = [e for e in _rumors(sid) if e.get("whisper") == whisper]
    if not heard:
        return None
    return bool(heard[-1].get("is_true"))


def verify(sid: str | None, whisper: str, verdict: str) -> dict:
    """Judge a whisper this session actually heard."""
    if verdict not in VERDICTS:
        raise ValueError("verdict must be 'true' or 'false'")
    truth = _truth_of(sid, whisper)
    if truth is None:
        return {
            "verified": False,
            "reason": "this session never heard that whisper",
        }
    correct = truth == (verdict == "true")
    journal.log(
        "desk_verdict", sid=sid, whisper=whisper,
        verdict=verdict, correct=correct,
    )
    return {
        "verified": True,
        "correct": correct,
        "fact": ("confirmed: " if truth else "debunked: ") + whisper,
    }


def facts(sid: str | None) -> list[dict]:
    """Derived world knowledge: what this session got right, and
    what it printed, in order."""
    out: list[dict] = []
    for e in journal.entries(sid):
        if e.get("kind") == "desk_verdict" and e.get("correct"):
            truth = _truth_of(sid, e.get("whisper", ""))
            out.append({
                "kind": "confirmed" if truth else "debunked",
                "text": e.get("whisper", ""),
            })
        elif e.get("kind") == "printed":
            out.append({"kind": "printed", "text": e.get("headline", "")})
    return out


def print_headline(sid: str | None, headline: str) -> dict:
    headline = str(headline or "").strip()
    if not headline:
        raise ValueError("a headline must say something")
    return journal.log("printed", sid=sid, headline=headline)


def prompt_lines(sid: str | None) -> str:
    """The world-knowledge block for generation prompts. Empty when
    the session knows nothing yet - silence, not filler."""
    known = facts(sid)
    if not known:
        return ""
    lines = ["WHAT THE WORLD KNOWS NOW:"]
    for f in known[-8:]:
        lines.append(f"  - {f['kind']}: {f['text']}")
    return "\n".join(lines) + "\n"
