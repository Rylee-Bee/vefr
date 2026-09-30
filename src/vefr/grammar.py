"""Pack grammars - a tiny seeded expander, so a pack keeps its voice
offline with no model and no baked pool.

A grammar is data an author writes by hand in `world.json`:

    "grammars": {
      "whisper": {"origin": ["#who# says #news#."],
                  "who": ["the innkeeper"],
                  "news": ["the road east is watched"]}
    }

It maps a rule name to a non-empty list of strings. Expansion starts
at `origin`; every `#rule#` inside a string expands to one entry of
that rule, chosen from the seeded rng; every other character is kept
as it was written. Three rules keep it safe:

  - `origin` is required (a grammar without one expands to nothing);
  - every `#rule#` must name a rule that exists in the same grammar;
  - at most `MAX_EXPANSIONS` (200) entries are drawn in one call, so a
    grammar that points at itself stops rather than loops.

A reference that does not resolve, or a cap that trips, returns the
empty string - the same honest silence the composer keeps when a pack
has nothing to say, never a half-built or half-invented line.

Deterministic and offline by construction: the only randomness is the
`random.Random` the caller hands in, and nothing here reads a clock,
the network, or a model. The same seed and the same grammar always
give the same sentence.

The player's own copy of this algorithm lives in `web/packaged.html`
(`grammarExpand`), so a woven file expands a grammar without the
engine. The two are behaviour-identical; they do not promise the same
sentence for the same seed, because each side's rng is its own.
"""

from __future__ import annotations

import random
import re

# How many entries one expansion may draw in total, references
# included. A grammar that feeds itself hits this and stops.
MAX_EXPANSIONS = 200

# A `#rule#` reference: word characters, then a dash or dot, ending
# at the closing `#`. Matches the player's own regex exactly.
REF = re.compile(r"#([A-Za-z0-9_][A-Za-z0-9_.-]*)#")


class _Refuse(Exception):
    """A reference did not resolve, or the expansion cap tripped."""


def _draw(entries, rng: random.Random, budget: list[int]) -> str:
    """One entry of a rule, or a refusal.

    `budget` is a one-slot list used as a counter, so the same draw
    budget is shared by every nested reference in one expansion.
    """
    if not isinstance(entries, list) or not entries:
        raise _Refuse
    if budget[0] <= 0:
        raise _Refuse
    budget[0] -= 1
    entry = entries[rng.randrange(len(entries))]
    if not isinstance(entry, str):
        raise _Refuse
    return entry


def _fill(grammar: dict, text: str, rng: random.Random, budget: list[int]) -> str:
    """Every `#rule#` in `text` replaced by one drawn expansion.

    A refusal anywhere aborts the whole expansion: the caller sees
    `_Refuse` and hands back the empty string, so a line is never
    published with a hole where a word should be.
    """
    def replace(match: re.Match) -> str:
        return _rule(grammar, match.group(1), rng, budget)

    return REF.sub(replace, text)


def _rule(grammar: dict, name: str, rng: random.Random, budget: list[int]) -> str:
    entry = _draw(grammar.get(name), rng, budget)
    return _fill(grammar, entry, rng, budget)


def expand(grammar: dict, rng: random.Random, *, limit: int = MAX_EXPANSIONS) -> str:
    """Expand `grammar` from its `origin` rule into one line of text.

    `rng` is the only source of randomness, so the same seed and the
    same grammar always give the same line. Returns the empty string
    when the grammar is not a mapping, when it has no `origin`, when a
    `#rule#` names a rule that does not exist, or when the expansion
    draws more than `limit` entries.

    The same algorithm runs in the woven player
    (`grammarExpand` in web/packaged.html).
    """
    if not isinstance(grammar, dict):
        return ""
    budget = [max(1, int(limit))]
    try:
        return _rule(grammar, "origin", rng, budget)
    except _Refuse:
        return ""


def expand_seeded(grammar: dict, seed, *, limit: int = MAX_EXPANSIONS) -> str:
    """`expand` with the seed built here: `random.Random(seed)`.

    The shape `norns delve` uses - one named floor, one seed, one
    name, the same name every time that seed is asked for.
    """
    return expand(grammar, random.Random(seed), limit=limit)
