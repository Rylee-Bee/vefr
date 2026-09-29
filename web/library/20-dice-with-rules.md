---
title: Dice With Rules
kind: book
shelf: how-vefr-works
short: How a computer, which always does the same thing, can still surprise you.
source: src/vefr/runes.py
---
Games need surprises, but computers can't really roll dice. Everything
a computer does, it does exactly the same way every time. Programmers
call that *deterministic*.

So how does a computer surprise you?

* * *

It fakes it. A little recipe takes a starting number and stirs it into
a long run of numbers that look random. The recipe is a *random number
generator*. The starting number is the *seed*.

Same seed, same numbers, every time. Different seed, different numbers.

* * *

At the Casting Table, the seed is made from the story's time of day
(dusk, dawn) and the current minute. So a cast holds still for a
minute, and then changes.

Casting three runes from twenty-four is a tiny piece of *procedural
generation*: making things from rules instead of by hand.

* * *

Why keep a seed at all? Because it lets you get the same surprise
back. Share a seed and a friend gets the exact same world. Hit a bug?
Replay the seed and it happens again, so you can fix it.

Making something happen again on purpose is *reproducing* it. It's the
first step of every fix.

* * *

Most of VEFR is deterministic on purpose: the map, the log, the saved
things. The runes are the one place chance lives. The story's big shape
is fixed; the cast is the surprise inside the shape.

Fighting works the same way: turn by turn, with fixed numbers. The
only surprise is what each side chooses to do.

* * *

**Try it.** Go to the Casting Table and cast. Cast again straight away:
same three runes, same seed. Wait for the clock to tick over to the
next minute and cast again: new runes.

You just watched a seed work.
