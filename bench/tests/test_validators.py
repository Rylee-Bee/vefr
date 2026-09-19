"""Validator crash-sweep: every registered validator must accept plausible
synthetic input without raising. This is a judge-integrity gate - a broken
judge would corrupt every run silently.

Run: python3 bench/cli.py judgecheck (or python3 bench/tests/test_validators.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bench.olympics import parse as P  # noqa: E402
from bench.olympics.tasks import ALL_TASKS  # noqa: E402
from bench.olympics.validators import VALIDATORS  # noqa: E402
from bench.cups.real_agent import AGENT_TASKS  # noqa: E402

HONEST_JSON = ('{"priority": {"urgent": [], "can_wait": [], "informational": []},'
               '"known_capital": "X", "unknown_planet_capital": "?",'
               '"unestablished_lore": "?", "category": "billing", "order": 1,'
               '"date": "d", "destination": "d", "total": 1, "decision": "accept",'
               '"user": {"name": "Ada"}, "refund_due": 5.0, "summary": "s",'
               '"carrier": "c", "window": "w", "budget": 9, "rec": "a",'
               '"package-5": "late", "tools": [], "rows": [{"user": {"name": "Ada"},'
               '"amount": 9}], "order_id": "3", "steps": [], "state": "ok"}')

STORY = ("The lantern keeper checked the empty far railings. A green scarf "
         "had been left on the bench by the harbor master, who then watched "
         "the dark water. \"The bridge is unsafe,\" said Sol. Mara shook her "
         "head. They waited under the flickering light while the well water "
         "ran low and the baked bread cooled at the table. The mist tasted "
         "of iron. Rain fell on the bakery roof. It reminded someone of the "
         "quiet dusk ferry ride home. So they stayed, saying little, until "
         "the lantern finally burned its one bright hour. Then the keeper "
         "walked to the old door and remembered a funeral from long ago.")


def build_meta(task):
    n = max(6, len(task.get("session") or []))
    if task.get("session"):
        replies = []
        for ex in task["session"]:
            if ex.get("give"):
                replies.append(ex["give"])
            else:
                replies.append(STORY)
        replies = replies if replies else [STORY] * n
        final = replies[-1]
    else:
        replies = [HONEST_JSON]
        final = HONEST_JSON
    return {"replies": replies, "final_raw": final,
            "messages": [], "session": bool(task.get("session"))}


def run():
    failures = []
    check = list(ALL_TASKS) + AGENT_TASKS
    seen = set()
    for t in check:
        vname = t.get("validator", "structured")
        vf = VALIDATORS.get(vname)
        if vf is None:
            failures.append((t["id"], f"no validator {vname}"))
            continue
        try:
            meta = build_meta(t)
            pr = P.parse(meta["final_raw"])
            d = vf(t, pr, meta)
            if not isinstance(d, dict) or "semantic" not in d:
                failures.append((t["id"], f"bad validator return {d!r}"))
        except Exception as e:
            failures.append((t["id"], f"{type(e).__name__}: {e}"))
        seen.add(t["id"])
    # make sure EVERY registered validator is reachable by some task
    for vname, vf in VALIDATORS.items():
        if not any(t.get("validator", "structured") == vname for t in check):
            failures.append(("(registry)", f"validator {vname!r} unreachable"))
            # still exercise it directly
            try:
                meta = build_meta({"session": [
                    {"user": "step one"}, {"user": "step two"},
                    {"user": "final json step"}]})
                meta["final_raw"] = HONEST_JSON
                d = vf({"id": "synthetic", "expect": {"stale_step": 3,
                       "weather_tool": "w", "per_turn": [],
                       "answer_path": "category", "want": "billing",
                       "tool_name": "t1", "args": {}}},
                       P.parse(HONEST_JSON), meta)
                assert isinstance(d, dict)
            except Exception as e:
                failures.append((f"(direct {vname})", f"{e}"))
    print(f"validator sweep: {len(check)} tasks checked, {len(failures)} issues")
    for fid, msg in failures:
        print(f"  FAIL {fid}: {msg}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())