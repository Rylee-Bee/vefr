---
title: The Rules of Your World
kind: book
shelf: how-vefr-works
short: Every world keeps its truth in one place, and the studio checks it before using it.
source: src/vefr/maplab.py
---
Every world needs one place where the truth lives. If the Keeper is
old in one room and young in another, something is broken.

Programmers call that one place the *source of truth*. Writers call
it the *story bible*. In VEFR, it's the Archives.

* * *

A world is really a folder of plain text files. The logbok holds the
rules. The map holds the ground. The voices hold the people. The ledger
keeps lines worth remembering.

Keeping data in plain files you can read is a choice. It means any
tool, and any person, can open them. Programmers call that an *open
format*.

* * *

Every file follows a shape: which parts go where, and what each part
may hold. That shape is a *schema*. A map must be a rectangle of
letters. Every letter needs a legend entry. The hero must start on
ground you can walk on.

* * *

Before the studio uses a world, it checks every one of those rules.
That's *validation*. A problem it finds is an *error*. A little problem
it can live with is a *warning*.

Checking early means a mistake shows up as a clear sentence in the
studio, not as a mystery later in the game.

* * *

When a helper writes something new, it reads the logbok first, every
time. The rules you write are the rules it follows. That's why they
should be short and clear: "Never explain. Show only."

* * *

**Try it.** Open the Archives and go down, step by step, through what
the studio knows about your world. Is anything missing that a helper
would need to know?

Open your world's folder, find `logbok.md`, and add one short rule.

That line is now a rule the whole studio obeys.
