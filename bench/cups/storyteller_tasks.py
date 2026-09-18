"""Storyteller Cup - which small models are enjoyable to write with?

Automated evidence is deterministic signals ONLY (slop, repetition, length,
probe-checked world-truth fidelity, dialogue variance, continuity keys,
steering). Enjoyability is decided by blind human pairs, produced separately.
Nothing here can award "taste"; it screens out the obviously-broken so we do
not waste the human's attention.

The VEFR-specific world/belief/state fixture is the heart: a character may
sincerely believe something false without the story flipping world truth.
"""

from ..olympics.prompts import prose_system

T = []
GET = {}  # reusable blocks


def add(tid, category, capability, system, user, validator="prose_signals",
        expect=None, role_critical=False, weight=1, max_tokens=520,
        temperature=0.85, name=None, session=None, world_truth=None):
    T.append({"id": f"story.{tid}", "cup": "storyteller", "category": category,
              "capability": capability, "name": name or capability,
              "system": system, "user": user, "validator": validator,
              "expect": expect or {}, "role_critical": role_critical,
              "weight": weight, "temperature": temperature,
              "max_tokens": max_tokens, "session": session,
              "world_truth": world_truth})


WORLD_BRIDGE = {
    "world": ("WORLD TRUTH (authoritative, do not contradict):\n"
              "  - The bridge is unsafe.\n"
              "  - Repair report #7 was filed Sep 8 and has not been verified.\n"
              "  - The bake sale is Saturday."),
    "beliefs": ("CHARACTER BELIEFS (what characters think, not world truth):\n"
                "  - Mara believes the bridge was repaired yesterday.\n"
                "  - Sol suspects the repair report was forged."),
    "probe": {"expect_low": "no"},
    "forbid_in_story": ["the bridge was truly repaired", "the bridge is safe",
                        "the bridge had been safely repaired",
                        "the bridge was fine"],
}


def _story_session(world_msg, request, followups, probe):
    """Build a session: world+request -> story, then each followup -> reply,
    then probe -> reply. Pre-scripted 'give' items can seed continuity."""
    s = [{"system": prose_system(["Write prose only. Use the supplied world "
                                  "and character beliefs as written."]) + "\n" + world_msg,
          "user": request}]
    for fu in followups:
        if isinstance(fu, dict) and fu.get("give"):
            s.append({"give": fu["give"]})
        else:
            s.append({"user": fu})
    if probe:
        s.append({"user": probe})
    return s


# --------------------------------------------------------------------------
# SIX-STYLE PROSE SPREAD (raw recorded; role-critical false)
# --------------------------------------------------------------------------
STYLE_PROMPTS = [
    ("quiet", "Write a quiet scene of two people waiting for a ferry in the "
              "early morning. Short, restrained, ~120 words."),
    ("comedy", "Write a short comedic scene where a museum guard tries to "
               "sneak a sandwich past a very serious statue. ~120 words."),
    ("tension", "Write a tense scene: someone is checking a locked workshop "
                "door from the outside. Someone is inside. ~120 words."),
    ("speculative", "Write a short speculative scene about a town where the "
                    "sky is visited by a quiet visitor. ~120 words."),
    ("weird", "Write a short, whimiscal scene about a bakery that only opens "
              "when it is raining. ~120 words."),
    ("mundane", "Write a short scene of a person returning home with "
                "unexpected groceries. No drama. ~120 words."),
]
for i, (key, prompt) in enumerate(STYLE_PROMPTS):
    add(f"style{i}", "prose", "style_spread",
        prose_system(["Write fiction only. No meta commentary, no titles."]),
        prompt, name=f"style:{key}", max_tokens=380)

# --------------------------------------------------------------------------
# WORLD vs BELIEF vs STATE (the VEFR fixture)
# --------------------------------------------------------------------------
WR = (WORLD_BRIDGE["world"] + "\n\n" + WORLD_BRIDGE["beliefs"])
add("world1", "fidelity", "character_false_belief_without_flipping_world",
    None, None, validator="world_belief", world_truth=WORLD_BRIDGE,
    role_critical=True, weight=3, max_tokens=560, name="belief vs world truth",
    session=_story_session(
        WR,
        'Write a short scene: Mara confidently proposes using the bridge '
        'today; Sol quietly declines citing the report. Let the disagreement '
        'stay unresolved. ~150 words.',
        [{"give": "The scene continues with Sol at the bake-sale table, "
                  "watching the bridge from afar."},
         "Finish with one small beat: someone asks Mara why she is not on "
         "the bridge. Show her noticing the empty far railings."],
        "What is the current, authoritative state of the bridge? Answer with "
        "exactly 'yes' or 'no' after the word STATE:"))

add("world2", "fidelity", "world_probe_after_story",
    None, None, validator="world_probe", role_critical=True, max_tokens=520,
    name="world truth survives a scene",
    session=_story_session(
        "WORLD TRUTH:\n  - The well is the only water source.\n"
        "  - The tank's gauge reads EMPTY.\n",
        'Write a short scene where a caretaker checks the tank gauge and '
        'reacts. ~120 words.',
        [],
        "Based ONLY on world truth, is the tank empty now? Answer with "
        "exactly 'yes' or 'no' after the word STATE:"),
    expect={"probe_contains": "yes"})

# --------------------------------------------------------------------------
# CONTINUITY
# --------------------------------------------------------------------------
add("cont1", "continuity", "item_travels_turns",
    None, None, validator="continuity", role_critical=True, max_tokens=420,
    name="continuity across continuations",
    session=_story_session(
        "WORLD TRUTH:\n  - A green scarf was left on the bench.\n",
        "Write a two-sentence opening: a person finds something on a bench.",
        ["Continue: half a day later, the thing is not there. What happened?",
         "End with the thing coming back into the story."],
        None),
    expect={"must_keep": ["scarf", "bench"]})

# --------------------------------------------------------------------------
# STEERING / RECOVERY
# --------------------------------------------------------------------------
add("steer1", "steer", "rewrite_on_redirection",
    None, None, validator="steer", role_critical=True, max_tokens=460,
    name="steering changes the scene",
    session=_story_session(
        "WORLD TRUTH:\n  - The fair runs all weekend.\n",
        "Open a scene at the fair on Saturday: two friends, a spilled "
        "drink, a laugh.",
        ["Actually the scene is at a funeral on Monday. Rewrite the opening "
         "thirty words to fit, keeping the friends."],
        None),
    expect={"steer_in_final": "funeral", "no_old_in_final": "fair"})

# --------------------------------------------------------------------------
# DIALOGUE DISTINCTNESS
# --------------------------------------------------------------------------
add("dlg1", "dialogue", "voices_do_not_bleed",
    None, None, validator="dialogue_distinct", max_tokens=420,
    name="distinct voices",
    session=_story_session(
        "WORLD TRUTH:\n  - The two door-lights are out, one flickers.\n",
        'Write a dialogue-heavy scene (>=4 quoted lines) between the strict '
        'harbor master and the easygoing boatwright over the flickering '
        'light. ~130 words.',
        [], None))

# --------------------------------------------------------------------------
# LORE USE (supplied lore enriches, not dumps)
# --------------------------------------------------------------------------
LORE = ("LORE (facts the tale may use):\n"
        "  - The lantern works one hour each evening.\n"
        "  - The well is the only water source.\n"
        "  - Sky mist is edible but tastes of iron.\n")
add("lore1", "lore", "lore_enriches",
    None, None, validator="lore_use", max_tokens=460,
    name="lore use without exposition dump",
    session=_story_session(
        LORE,
        "Write a short scene about the lantern keeper's evening round. "
        "Weave in at least one piece of lore quietly. ~130 words.",
        [], None),
    expect={"lore_keys": ["lantern", "well", "mist"], "min_used": 1})

# --------------------------------------------------------------------------
# EMOTION: emergent, not narrated
# --------------------------------------------------------------------------
add("emo1", "emotion", "emergent_not_narrated",
    None, None, validator="no_em_dump", max_tokens=400,
    name="emotion from scene, not narration",
    session=_story_session(
        "WORLD TRUTH:\n  - The last train of the night left at 23:40.\n",
        "Write a short scene about someone who misses the last train on "
        "purpose. Show, do not label the feeling. ~120 words.",
        [], None))

# --------------------------------------------------------------------------
# LONGFORM + SURPRISE (multi-turn degradation tracked)
# --------------------------------------------------------------------------
add("long1", "longform", "four_turn_survival",
    None, None, validator="prose_signals", role_critical=False, weight=2,
    max_tokens=520, temperature=0.85, name="longform across turns",
    expect={"range": (40, 400)},
    session=_story_session(
        "WORLD TRUTH:\n  - The observatory door was welded shut in 2007.\n",
        "Start a short mystery: a night watchman hears tapping from inside "
        " the sealed observatory. ~130 words.",
        ["Two nights later the tapping has a rhythm. Continue.",
         "The watchman decides to act. Continue, without resolving the mystery.",
         "A third person - the director - appears. End this installment "
         "unresolved."],
        None))

STORYTELLER_TASKS = list(T)