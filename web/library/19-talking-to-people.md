---
title: Talking to People
kind: book
shelf: how-vefr-works
---
Anyone in a game who isn't the player is an *NPC*, a *non-player
character*. The shopkeeper, the guard, the Keeper at the stone.

What they say is *dialogue*. Writing it is part of *narrative design*.

* * *

Many games write every line by hand, and the player picks answers from
a list. Each pick leads down a different path. That shape is a
*dialogue tree*.

VEFR's people work a different way. Each one has a *voice file*: a
short description of who they are and how they speak. A small AI model
reads it and writes a fresh line each visit.

* * *

A voice file looks like this:

```
You are the Keeper of the stone in Emberfield.
- Speak in short sentences: 1-3 of them.
- No modern words. Never explain. Show only.
```

That's a *prompt*: instructions a model reads first. A description of a
character's look, voice, and wants is a *character sheet*.

* * *

What if the model is switched off, or slow? Each character also keeps a
little bank of hand-written lines. If the model can't answer, one of
those speaks instead, so the world never goes silent.

Programmers call that a *fallback*. Planning for things going wrong is
*graceful degradation*, and it's a sign of a careful builder.

* * *

The model's answer has to come back in an exact shape: who spoke, and
the line. Anything else is thrown away. That exact shape is a *schema*,
and checking against it is *validation*.

* * *

**Try it.** Walk the town and talk to someone twice. Two different
lines, same voice.

Then open your world's folder and look in `voices/`. Read their voice
file, and add one line to their fallback bank (the file ending in
`.fragments.md`), in their voice. You just wrote dialogue.
