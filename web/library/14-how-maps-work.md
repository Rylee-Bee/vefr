---
title: How Maps Work
kind: book
shelf: how-vefr-works
short: A game map is graph paper: every square holds one kind of ground.
source: src/vefr/maplab.py
---
A map is graph paper. Every square holds one kind of ground: grass,
path, wall, water. That's all a map is, underneath.

Real studios call each square a *tile*, the paper a *grid*, and the
box of pictures you paint with a *tileset*. Making maps is called
*level design*.

* * *

Underneath the pictures, a map is just letters in a text file:

```
############
#..p.......#
#..p..S....#
############
```

`#` is a wall, `.` is grass, `p` is path, `S` is a stone. One letter,
one square. Turn on **Show me how things work** in the Map Room to see
the letters on your own map.

* * *

A little list says what each letter means. That list is the *legend*,
just like the key on a paper map.

The legend also says which squares are *solid*. The player can't walk
through solid squares. Games call this *collision*.

Some squares have a job. A safe square is a *sanctuary*: nothing can
hurt you there. The square where the hero starts is the *spawn point*.

* * *

Special places get names: "the stone", "the threshold". When the hero
stands there, the name shows up. Games call these *points of interest*.

Some maps are drawn by hand. Others are built by the game from rules
as you play. That's *procedural generation*, and the Rune Room is
where it lives.

* * *

**Try it.** Go to the Map Room and turn on **Show me how things work**.
Pick the wall brush and paint a wall right where the hero starts. Then
press **Check the map**.

It tells you the hero's starting square isn't walkable. That's a *test*
catching a *bug*. Paint the ground back and check again: you just did
*debugging*. Nothing was kept, because the map only changes when you say
so.
