"""Task registry: aggregation + frozen qualification set + category filters.

Freezing policy (suite versioning):
  - QUALS (frozen qualification set): onboarding gate every new participant
    runs; stable across suite versions.
  - FULL: everything; changes freely during .0.x research, frozen at 1.0.
  - Holdout set is NOT mixed in here - it lives in cups as raw fixtures and
    is only ever run after a version is frozen (or explicitly flagged).
"""

from bench.cups.hermod_tasks import HERMOD_TASKS
from bench.cups.assistant_tasks import ASSISTANT_TASKS
from bench.cups.storyteller_tasks import STORYTELLER_TASKS
from bench.cups.flex_tasks import FLEX_TASKS

ALL_TASKS = HERMOD_TASKS + ASSISTANT_TASKS + STORYTELLER_TASKS + FLEX_TASKS
BY_ID = {t["id"]: t for t in ALL_TASKS}

CUPS = ("hermod", "assistant", "storyteller", "flexibility")

# Tasks whose judge/task definition was corrected after batch runs started
# (suite 0.4.1). A run in stage "patch" supersedes earlier trials of the same
# task; summaries drop the old trials for these ids.
PATCHED = {
    "hermod.struct2": "0.4.1 task now supplies the facts it demands",
    "assist.fu1": "0.4.1 judge accepts the correct waiting-on person",
}

# Frozen qualification set (research version 0.4; will be re-frozen at 1.0).
# Rule: every role-critical task is included; every category is represented;
# heavy storytelling longform is deferred to semifinal/full.
QUALS = [
    # hermod - instruction / structure
    "hermod.inst4", "hermod.struct2",
    # hermod - tool judgment & selection & args (the canaries)
    "hermod.tj1", "hermod.tj2", "hermod.tj2b", "hermod.tj3", "hermod.tj4",
    "hermod.tj5", "hermod.tj6",
    "hermod.ts1", "hermod.ts2",
    "hermod.ta1",
    # hermod - evidence / authority / unknown / verification
    "hermod.unk1", "hermod.src1", "hermod.src2", "hermod.stale1",
    "hermod.contra2", "hermod.auth1", "hermod.auth2", "hermod.verify1",
    "hermod.help1",
    # hermod - robustness / practical breadth
    "hermod.mal1", "hermod.ext2", "hermod.tr1", "hermod.cls1",
    "hermod.cls3", "hermod.reason1", "hermod.reason2",
    # assistant - judgment & restraint & clippy
    "assist.triage1", "assist.brief1", "assist.fu1", "assist.draft1",
    "assist.deleg1", "assist.intr1", "assist.rest1", "assist.unkA1",
    "assist.reconcile1", "assist.longrun1", "assist.toolA2", "assist.comm1",
    "assist.comm2", "assist.comm3", "assist.clippy1",
    # storyteller - fidelity and shape
    "story.world1", "story.world2", "story.cont1", "story.steer1",
    "story.style0",
    # flexibility - switching & distractors
    "flex.switch1", "flex.shift1", "flex.dist1", "flex.breadth1",
    "flex.dist3",
]


def _ids_valid():
    missing = [i for i in QUALS if i not in BY_ID]
    if missing:
        raise SystemExit(f"qual set references unknown task ids: {missing}")
    return True


_ids_valid()


def qualifier():
    return [BY_ID[i] for i in QUALS]


def full():
    return ALL_TASKS


def category(cup=None, category=None, capability=None):
    out = ALL_TASKS
    if cup:
        out = [t for t in out if t["cup"] == cup]
    if category:
        out = [t for t in out if t["category"] == category]
    if capability:
        out = [t for t in out if t["capability"] == capability]
    return out


def events():
    """Event-level mapping for scoring: category-level pass rates."""
    from collections import defaultdict
    d = defaultdict(set)
    for t in ALL_TASKS:
        d[(t["cup"], t["category"])].add(t["id"])
    return {k: list(v) for k, v in d.items()} | {
        "flexibility": ["flex.switch1", "flex.shift1", "flex.breadth1"]}


def count():
    return {c: len(category(cup=c)) for c in CUPS} | {"total": len(ALL_TASKS)}