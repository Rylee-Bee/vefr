---
title: Saving Your Work
kind: book
shelf: how-vefr-works
short: How the studio makes sure you never lose what you made.
source: src/vefr/journal.py
---
Losing work is the worst feeling in making things. Every good tool is
built around one promise: you won't lose it.

* * *

On the Map Room's drawing table, every brush stroke is remembered, so
**undo** can step back. The list of steps is an *undo stack*: the newest
on top, taken off one at a time.

Nothing you sketch changes your real map until you say so. A place to
try things safely is a *sandbox*, or a *draft*.

* * *

When you do replace your map, the studio first copies the old one
beside it, stamped with the date and time. That copy is a *backup*.
Going back to it is a *restore*.

* * *

The Chronicle writes down everything that happens, in order, adding
each new thing at the end. A list that only grows is a *log*. Programmers say
it's *append-only*.

Each new line is written to a spare page first, then swapped in all at
once. If the power cuts out halfway, you might lose the newest line,
never the whole book. That trick is an *atomic write*.

* * *

Pressing **Keep** says "this one matters". It lands in the Hall with
everything else you've kept. Programmers call saving something for
good a *commit*, and the whole list of them *version control*. It's
how whole teams of people build one thing together without losing
anyone's work.

* * *

**Try it.** In the Map Room, paint three squares, then press **undo** three
times. Each press takes back one stroke, newest first.

That's a stack. Last in, first out.
