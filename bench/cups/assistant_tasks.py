"""Assistant Cup - would Rylee want this beside her all day?

Judgment, prioritization, restraint, communication, initiative, interruption
decisions, no invented facts, no Clippy behavior. Most events are natural
language in; some are structured. Validators are deterministic; the human
preference pairs live separately in bench/reports/.

A lot of assistant correctness is "what did they decide about scarce
attention" - so several validators measure included/omitted topics, brevity,
and unsolicited-offer counts rather than exact strings.
"""

from ..olympics.prompts import json_system, prose_system
from . import toolkit as K
from ..olympics.prompts import tool_system, msgs

T = []


def add(tid, category, capability, system, user, validator="structured",
        expect=None, role_critical=False, weight=1, temperature=None,
        max_tokens=None, name=None, session=None):
    T.append({"id": f"assist.{tid}", "cup": "assistant", "category": category,
              "capability": capability, "name": name or capability,
              "system": system, "user": user, "validator": validator,
              "expect": expect or {}, "role_critical": role_critical,
              "weight": weight, "temperature": temperature,
              "max_tokens": max_tokens, "session": session})


# --------------------------------------------------------------------------
# INBOX TRIAGE
# --------------------------------------------------------------------------
add("triage1", "triage", "prioritize_today",
    json_system(["Classify each item into exactly one bucket.",
                 "urgent = blocks today's work; can_wait = this week; "
                 "informational = no action."]),
    'Inbox:\n'
    'M1: "Build failing on main, please fix before standup."\n'
    'M2: "Team lunch signup closes Monday."\n'
    'M3: "Quarterly report published."\n'
    'Return JSON {"priority": {"urgent": ["?"], "can_wait": ["?"], '
    '"informational": ["?"]}} using message ids like "M1".',
    validator="triage",
    expect={"urgent": ["M1"], "can_wait": ["M2"], "informational": ["M3"]},
    name="inbox triage", role_critical=True)

# --------------------------------------------------------------------------
# CALENDAR JUDGMENT
# --------------------------------------------------------------------------
add("cal1", "calendar", "conflict_detection",
    json_system(["Find conflicts in the supplied calendar."]),
    'Calendar:\n'
    '09:00-10:00 deep work\n10:00-11:00 1:1 with Ada\n11:30-12:00 vet appt\n'
    'Return JSON {"conflicts": ["?"], "note": "one sentence if none"}',
    expect={"require_keys": ["conflicts"]}, name="calendar conflicts")
add("cal2", "calendar", "buffer_and_travel",
    json_system(["Respect travel time not shown in the calendar."]),
    'Calendar: 13:00-13:30 call at home office; 15:00-16:00 client mtg at '
    'downtown office, 25 min away.\nReturn JSON {"advice": "?"}',
    expect={"require": {"advice": {"contains": "leave"}}}, name="travel buffer")

# --------------------------------------------------------------------------
# MORNING BRIEF
# --------------------------------------------------------------------------
add("brief1", "brief", "compression",
    prose_system(["Write a morning brief of at most 5 bullet lines.",
                  "Include what matters today; do not include noise."]),
    'Events today: 10:00 release demo (must prep), 14:00 dentist, server '
    'certificate renews Friday, new starter Ada arrives, t-shirts for the '
    'offsite are being printed, build pipeline update email.',
    validator="brief",
    expect={"must_mention": ["demo", "dentist"],
            "avoid_mention": ["t-shirt", "offsite"], "max_words": 160},
    name="morning brief", role_critical=True)

# --------------------------------------------------------------------------
# FOLLOW-UP (prior context supplied)
# --------------------------------------------------------------------------
add("fu1", "followup", "promises_and_waiters",
    json_system(["Report only what the record supports."]),
    'Project notes:\n- 08-30 I promised to send Ada the schema by 09-02\n'
    '- 09-03 Ada reminded me; on 09-04 I said I would send it Friday\n'
    '- Morgan waiting on our pricing response\n'
    'Return JSON {"my_commitment": "?", "status": "overdue/current", '
    '"waiting_on_me": ["?"], "waiting_on_others": ["?"]}',
    expect={"require": {"waiting_on_me": {"contains": "Ada"}},
            "forbid": {"my_commitment": {"eq": None}}},
    name="follow-up from notes", role_critical=True)

# --------------------------------------------------------------------------
# DRAFTING
# --------------------------------------------------------------------------
add("draft1", "drafting", "tone_and_facts",
    prose_system(["Draft a short email to the vendor declining extended "
                  "support, based ONLY on context.", "No invented reasons."]),
    'Context: we decided to drop the extended-support renewal after the July '
    'outage; the contract ends 10-31. Vendor name: Northwind Services.\n'
    'Write a polite 3-sentence email.',
    validator="no_invented",
    expect={"must_mention": "10-31",
            "must_not_claim": ["increase", "price", "cost", "lawsuit"]},
    name="draft without inventing", role_critical=True)

# --------------------------------------------------------------------------
# DELEGATION (can do / propose / needs authorization / needs human / needs Source)
# --------------------------------------------------------------------------
add("deleg1", "delegation", "authorization_boundary",
    json_system(["classify the requested action into exactly one bucket.",
                 "buckets: can-do, propose, needs-authorization, needs-human, "
                 "needs-source"]),
    'Request: "Approve the $12,000 software renewal."\nYou can draft the '
    'recommendation but the approval is not yours.\n'
    'Return JSON {"bucket": "?"}',
    expect={"require": {"bucket": {"eq": "needs-authorization"}}},
    name="delegation boundary", role_critical=True)

# --------------------------------------------------------------------------
# INTERRUPTION JUDGMENT
# --------------------------------------------------------------------------
add("intr1", "interruption", "should_not_interrupt",
    json_system(["For each event choose interrupt or defer. Interrupt only "
                 "for things that truly cannot wait 20 minutes."]),
    'While Rylee is in a 1:1 meeting, these arrive:\n'
    'E1: build red on main (team-wide)\nE2: 2FA code (expires in 2 min)\n'
    'E3: newsletter digest\nE4: new comment on a blog post\n'
    'Return JSON {"interrupt": ["?"], "defer": ["?"]}',
    expect={"require": {"interrupt": {"any_of": [["E2"], ["E1", "E2"]]}}},
    name="interrupt vs defer", role_critical=True)
add("intr2", "interruption", "must_interrupt",
    json_system(["Interrupt only for true blockers."]),
    'Rylee is deep in work. Incoming: production checkout is down for all '
    'customers; someone left a positive Yelp review; calendar reminder for '
    'lunch; teammate asks a "quick question" about feature X design.\n'
    'Return JSON {"interrupt": ["?"]}',
    name="must interrupt when catastrophe")

# --------------------------------------------------------------------------
# INITIATIVE / RESTRAINT
# --------------------------------------------------------------------------
add("init1", "initiative", "useful_next_step",
    prose_system(["If a genuinely useful next action exists, state exactly "
                  "one. Otherwise answer 'No action.'", "Do not manufacture "
                  "chores."]),
    'Context: draft of the release notes is done; the sign-off checklist '
    'needs the CEO to approve; you are Rylee, who owns the checklist.\n'
    'Return JSON {"next_action": "?"}',
    name="one useful next action")
add("rest1", "restraint", "correct_answer_is_nothing",
    prose_system(["The appropriate response may be to do nothing. Answer "
                  "with one short sentence."]),
    'Rylee says: "Remind me to water the plants." The reminder app already '
    'has this saved from last week. Do not re-save it.',
    validator="final_reply",
    expect={"required_in_final": [], "forbidden_in_final": ["saved", "added", "set a reminder"]},
    name="restraint: nothing to do", role_critical=True)

# --------------------------------------------------------------------------
# UNKNOWN (assistant)
# --------------------------------------------------------------------------
add("unkA1", "unknown", "no_plausible_invention",
    json_system(["If your answer needs a fact you do not have, write UNKNOWN."]),
    'Meeting invitation has no location attached: "Team sync, Tuesday 10:00", '
    'no room, no link.\nReturn JSON {"location": "?"}',
    validator="unknown",
    expect={"unknown_fields": ["location"]}, name="unknown location")

# --------------------------------------------------------------------------
# SOURCE RECONCILIATION
# --------------------------------------------------------------------------
add("reconcile1", "source", "chronology_and_authority",
    json_system(["Use the newest authoritative source. Older low-authority "
                 "info is overridden."]),
    'Calendar (updated today): "Budget review moved to Friday 15:00."\n'
    'Old email (last week): "Budget review Thursday 15:00."\n'
    'Return JSON {"budget_review": "?"}',
    expect={"require": {"budget_review": {"contains": "friday"}}},
    name="reconcile calendar vs email", role_critical=True)

# --------------------------------------------------------------------------
# LONG-RUN CONTEXT (session across interactions)
# --------------------------------------------------------------------------
LONG_SESSION = [
    {"system": json_system(["Remember the current objective and prior decisions."])
     + "\nObjective: move the offsite catering to a venue that is wheelchair "
     "accessible, approved budget $40k, before September 30.", "user": "Log: "
     "candidate venues: The Mill (historic, has stairs), Sunrise Hall (lift, "
     "fits 90), Dock House (open yard, no lift). Record a short note about "
     "which are usable."},
    {"user": "One month later, Rylee says: we approved Sunrise Hall on the 12th. "
     "Update the log and keep today's date (today is Sep 12)."},
    {"give": 'LOG:\nobjective: accessible offsite before Sep 30, budget $40k\n'
             'venues: Mill (stairs) - not usable\nSunrise Hall (lift) - approved '
             'Sep 12\nDock House (no lift) - not usable\n'},
    {"user": "Now return JSON {\"venue\": \"?\", \"objective_deadline\": \"?\"} "
     "based on the log."},
]
add("longrun1", "longrun", "objective_survives",
    None, None, validator="final_state", session=LONG_SESSION,
    name="long-run objective preserved", role_critical=True,
    expect={"require": {"venue": {"eq": "Sunrise Hall"},
                        "objective_deadline": {"contains": "September 30"}}})

# --------------------------------------------------------------------------
# TOOL JUDGMENT (assistant)
# --------------------------------------------------------------------------
add("toolA1", "tool_judgment", "email_needed",
    tool_system([
        {"name": "send_email", "description": "Send an email to an address.",
         "parameters": {"type": "object",
                        "properties": {"to": {"type": "string"},
                                       "subject": {"type": "string"}},
                        "required": ["to", "subject"]}}]),
    'Rylee: "Email the final numbers to the board." The attachment and '
    'recipient list are ready in the draft.',
    validator="tool", expect={"decision": "must_call_tool", "tool_name": "send_email",
                              "args": {"to": {"contains": "."}, "subject": {"contains": ""}}},
    name="email needed")
add("toolA2", "tool_judgment", "no_tool_needed",
    tool_system([
        {"name": "search_docs", "description": "Full-text search the docs repo.",
         "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                        "required": ["query"]}},
        {"name": "send_email", "description": "Send an email.",
         "parameters": {"type": "object", "properties": {"to": {"type": "string"}},
                        "required": ["to"]}}]),
    'Rylee: "What is 12 * 9?" No tool is needed.',
    validator="tool", expect={"decision": "must_not_call"},
    name="no tool for arithmetic")

# --------------------------------------------------------------------------
# COMMUNICATION / FORMAT SWITCHING
# --------------------------------------------------------------------------
add("comm1", "communication", "tiny_answer",
    prose_system(["Answer in at most 8 words."]),
    'What time is the 13:00 meeting? It is at 13:00. Hands-on precise.',
    validator="clippy", expect={"must_mention": "13", "max_words": 12},
    name="tiny answer no ceremony")
add("comm2", "communication", "structured_result",
    json_system(), 'Summarize: "Deploy done, tests green, 2 warnings." '
                   'Return JSON {"deploy": "?", "tests": "?", "warnings": 2}',
    expect={"require": {"deploy": {"eq": "done"}, "tests": {"eq": "green"},
                        "warnings": {"eq": 2}}},
    name="structured result on demand")

# --------------------------------------------------------------------------
# CHAT-ONLY SESSION: a conversation must never leak tool-call syntax
# --------------------------------------------------------------------------
add("comm3", "communication", "chat_stays_chat",
    prose_system(["You are speaking with a friend about a shared work "
                  "project. Plain chat only."]),
    None, validator="no_tool_in_session", role_critical=True,
    temperature=0.4, name="no tool calls leak into chat",
    session=[
        {"user": "Did the bridge load test result come back yet?"},
        {"give": "It did - green, with a note about the far railings."},
        {"user": "Great. What should we look at next, the mist or the "
                 "lantern circuit?"},
    ])

# --------------------------------------------------------------------------
# CLIPPY SPIKE (explicit anti-annoyance)
# --------------------------------------------------------------------------
add("clippy1", "clippy", "no_unsolicited_offers",
    prose_system(["Answer the question. Do not offer further help, do not add "
                  "notes, do not follow up."]),
    'Rylee: "What time is the standup?" Given: standup is 09:30.',
    validator="clippy", expect={"must_mention": "09:30", "max_words": 25},
    name="clippy check", role_critical=True, weight=2)


ASSISTANT_TASKS = list(T)