---
title: The Engine Room
kind: book
shelf: how-vefr-works
short: The machine under every game that runs the rules and draws the world.
source: web/town.js
---
Under every game is a machine that runs the rules, draws the world,
and listens to the player. That machine is the *engine*.

Some studios build their own. Many use one someone else made. VEFR is
both: a studio and the engine underneath it.

* * *

Everything the game knows right now (where the hero stands, what they
carry, what time of day it is in the story) is its *state*. Draw the
state, and you see the world. Change the state, and the world changes.

* * *

Fast games, like racing games, use a *game loop*: many times a second,
check the buttons, move everything a little, draw it all again.

VEFR's town doesn't need that. It waits. When you press a key, it moves
the hero one square, checks nothing is in the way, draws the town, and
waits again. Waiting for something to happen, then answering it, is
*event-driven*. The key press is an *event*; the code that answers is
a *handler*.

* * *

When the hero tries to step onto a wall, the engine looks at that
square, sees it's solid, and simply doesn't move them. That tiny check
is *collision detection*.

* * *

The studio runs as a *server*: a program that waits for requests. The
pages you see are the *client*. They ask; it answers. Each kind of
question it can answer is an *API*.

The Boiler Room is where the local helper model is switched on and
off. It runs on your own computer, so nothing you write leaves the
house. That's *running locally*.

* * *

**Try it.** Walk the town using only W, A, S and D. Walk into a wall
on purpose. Nothing happens, and that nothing is a rule doing its job.

Now think: what would you change so a wall could be walked through?
(Hint: look in "How Maps Work" for the word *solid*.)
