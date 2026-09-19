"""Harness: run one participant over a list of tasks, recording every trial.

Pipeline per task:
  build context (single-turn or session)
  -> inference (llama-server, GPU)
  -> parse (raw preserved)
  -> validate (deterministic judge)
  -> record trial (full evidence line)

Sessions let us run multi-turn shapes (task switching, real-agent style,
story longform, tool-result feeding) through the same machinery. A session
turn may be:
  {"system": str, "user": str}      generate a reply
  {"user": str}                     append, generate
  {"give": "precomputed content"}   no inference, feed as assistant message
"""

import time

from . import parse as P
from .validators import VALIDATORS
from .records import TrialStore


def sanitize_messages(msgs):
    """Reduce a message list to shapes every GGUF chat template accepts.

    Some GGUF templates are strict about the transcript shape: Gemma3 rejects
    consecutive assistant turns AND any system turn that is not first;
    Qwen3.5 invites a 500 on any mid-conversation system message. Content is
    preserved verbatim; what changes is only where a block sits within the
    transcript, so the model still sees every instruction.

      - consecutive assistant turns are merged into one assistant message;
      - any system turn after the first is folded into the leading system.

    Returns (sanitized, notes) where notes counts each transform.
    """
    notes = {"merged_assistant": 0, "hoisted_system": 0}
    out = []
    lead = None
    for m in msgs:
        if m["role"] == "system":
            if lead is None:
                lead = m["content"]
                out.append({"role": "system", "content": lead})
            else:
                lead = lead + "\n\n" + m["content"]
                notes["hoisted_system"] += 1
                out[0] = {"role": "system", "content": lead}
        elif (m["role"] == "assistant" and out
              and out[-1]["role"] == "assistant"):
            out[-1] = {"role": "assistant",
                       "content": out[-1]["content"] + "\n\n" + m["content"]}
            notes["merged_assistant"] += 1
        else:
            out.append(m)
    return out, notes


def _replies_only(session):
    out = []
    for ex in session:
        if ex.get("give"):
            out.append(ex["give"])
        else:
            out.append("")  # placeholder for generated
    return out


def task_messages(task):
    """The exact user-visible prompt sequence for a task (for reports/pairs)."""
    if task.get("session"):
        msgs = []
        for ex in task["session"]:
            if ex.get("system"):
                msgs.append({"role": "system", "content": ex["system"]})
            if ex.get("give"):
                msgs.append({"role": "assistant", "content": ex["give"]})
            if ex.get("user"):
                msgs.append({"role": "user", "content": ex["user"]})
        return sanitize_messages(msgs)[0]
    return [{"role": "system", "content": task["system"]},
            {"role": "user", "content": task["user"]}]


def run_tasks(server, tasks, store, stage, temp_override=None):
    """Run tasks on a live server; write trials into store. Store must be open."""
    for task in tasks:
        trial = _run_one(server, task, temp_override)
        trial["stage"] = stage
        store.add_trial(trial)


def _run_one(server, task, temp_override):
    t0 = time.time()
    transforms = {"merged_assistant": 0, "hoisted_system": 0}
    session = task.get("session")
    if session:
        (replies, reasoning, finishes, msgs, total_lat, tin, tout,
         transforms) = _run_session(server, task, temp_override)
        final_raw = replies[-1] if replies else ""
        pr_final = P.parse(final_raw)
        pr_record = pr_final
    else:
        msgs = [{"role": "system", "content": task["system"]},
                {"role": "user", "content": task["user"]}]
        r = server.chat(msgs, temperature=temp_override or task.get("temperature"),
                        max_tokens=task.get("max_tokens"))
        replies = [r["content"]]
        reasoning = [r["reasoning"]]
        finishes = [r["finish_reason"]]
        final_raw = r["content"]
        total_lat = r["latency_s"]
        tin, tout = r["tokens_in"], r["tokens_out"]
        pr_final = P.parse(final_raw)
        pr_record = pr_final

    meta = {"replies": replies, "final_raw": final_raw,
            "messages": msgs, "session": bool(session),
            "replies_reasoning": reasoning,
            "finish_reasons": finishes,
            "transforms": transforms}
    vf = VALIDATORS.get(task.get("validator", "structured"))
    dims = vf(task, pr_record, meta) if vf else {"semantic": False, "protocol": False,
                                                 "evidence": "no validator"}
    overall = all(dims.get(k) for k in ("semantic", "protocol"))

    trial = {
        "task_id": task["id"],
        "cup": task.get("cup"),
        "category": task.get("category"),
        "capability": task.get("capability"),
        "role_critical": task.get("role_critical", False),
        "weight": task.get("weight", 1),
        "messages": msgs,
        "replies": replies,
        "replies_reasoning": reasoning,
        "finish_reasons": finishes,
        "truncated": any(f == "length" for f in finishes),
        "transforms": transforms,
        "final_raw": final_raw,
        "parse": pr_record,
        "dims": dims,
        "pass": overall,
        "epoch_s": round(time.time() - t0, 3),
        "latency_s": round(total_lat, 3),
        "tokens_in": tin,
        "tokens_out": tout,
    }
    return trial


def _run_session(server, task, temp_override):
    msgs = []
    replies = []
    reasoning = []
    finishes = []
    total_lat = 0.0
    tin = tout = 0
    transforms = {"merged_assistant": 0, "hoisted_system": 0}
    for ex in task["session"]:
        if ex.get("give"):
            msgs.append({"role": "assistant", "content": ex["give"]})
            replies.append(ex["give"])
            continue
        if ex.get("system"):
            msgs.append({"role": "system", "content": ex["system"]})
        if ex.get("user"):
            msgs.append({"role": "user", "content": ex["user"]})
        msgs, notes = sanitize_messages(msgs)
        for k in transforms:
            transforms[k] += notes[k]
        r = server.chat(msgs, temperature=temp_override or task.get("temperature"),
                        max_tokens=task.get("max_tokens"))
        replies.append(r["content"])
        reasoning.append(r["reasoning"])
        finishes.append(r["finish_reason"])
        msgs.append({"role": "assistant", "content": r["content"]})
        total_lat += r["latency_s"]
        tin += r["tokens_in"] or 0
        tout += r["tokens_out"] or 0
    msgs, notes = sanitize_messages(msgs)
    for k in transforms:
        transforms[k] += notes[k]
    return replies, reasoning, finishes, msgs, total_lat, tin, tout, transforms