# 0004 - Scoped rules

Date: 2026-10-02

## Status

Proposed

## Context

The rules engine is deliberately small (design/rules-when-then.md):
no priorities, no chains, rules run in the order written, `once` is
the default, and `RULE_LIMIT = 40` rules per game (maplab.py).
One rule is one sentence a person can read aloud.

An independent pack hit exactly 40 (finding 13 in
docs/research/2026-10-02-first-independent-pack.md). It did not ask
for a bigger number; it asked what the number is for.

What the 40 protects:

- **Readability.** Forty sentences a person can hold in one
  sitting. A hundred is a script you can only debug with tooling.
- **The why-log.** Every fired rule writes one plain journal line
  ("rule 'cat-notices' fired because ..."). Forty writers keep the
  **Why did that happen?** panel answerable by a human; more turns
  the panel into archaeology.
- **Authoring discipline.** A ceiling forces the author to decide
  what the world actually notices. That choice is design work, and
  a limit is what demands it.

What scoping must not become: a way around the ceiling. Four scopes
of forty is 160 rules, and the stack is unreadable again. Any second
scope has to be as tight as the first - same vocabulary, same law,
a number small enough to read.

## Decision

**Keep 40 global rules. Do NOT raise the global constant without
evidence.**

Add region-local rules as a second bounded scope:

- A region's `contract.json` may declare its own `rules` list.
- At most 16 per region, checked by the validator with a plain
  error naming the region.
- **Same vocabulary:** the same events, conditions and actions the
  global rules use. No new event exists to serve a region.
- **Same no-chains law:** a rule cannot cause another rule's event,
  no priorities, written order is the order, `once` stays default.
- **Fixed run order:** for an event that happens in a region, the
  global rules run first in written order, then that region's rules
  in written order. A region's rules see only events in their own
  region; global rules see everything. The scope order is printed
  in the docs and the why-log - it is not a priority knob anyone
  can turn.
- The why-log names the scope of every fired line: "global rule
  ..." versus "region 'cellar' rule ...".

Raising the global 40 later stays possible, but only with evidence:
a pack that exhausted region scoping and can name what the extra
global rules are for.

**Non-goal for now: per-visit rules.** Re-arming rules, visit-scoped
flags, and rules that exist only during a stay are out of scope.
Say it when evidence arrives; do not pre-build it.

## Consequences

It costs:

- The validator, engine, why-log and studio each carry a scope
  field from now on (maplab.py, the rule checker, the panel).
- The conflict warning must compare within a scope; the fixed
  cross-scope order replaces the need for a cross-scope priority.
- Docs grow one section (docs/guides/rulesets.md plus the design
  note) explaining the two scopes and the run order.

It does NOT:

- Raise the 40 global rules or add a third scope.
- Add priorities, chains, numbers, timers, randomness or a model
  call to the rules engine.
- Let a region rule name another region, a global rule, or a rule
  id - regions stay unaware of each other.
- Make scoping implicit: a region with no declared `rules` behaves
  exactly as today, and every existing pack loads unchanged.
- Decide per-visit semantics; that is named as a non-goal, not
  scheduled.
