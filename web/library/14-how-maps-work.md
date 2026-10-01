---
title: How Maps Work
kind: book
shelf: how-vefr-works
short: A game map is graph paper — every square holds one kind of ground.
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

The people and things standing on a map are *sprites*: small pictures
placed on squares. A game can bring its own, so the hero and the people
look like themselves instead of a dot.

A door - or the stair - can lead to another map. Games call that a
*transition*: the town outside and the entry room inside are two maps
joined by one door. Stand on the door and use it - press F, or tap
Interact - and you are in the room. A door is used, never walked through,
so passing a doorway does not carry you off. The room can be small and
exact, the way a real inside is.

* * *

A map can be dark until you have walked it. Games call that *fog of war*:
a small circle around you is lit, the ground you have crossed stays as a
dim memory, and the rest is black. A world says which of its maps are
dark - a town is open, and the floors below are dark.

* * *

A map can be bigger than the screen. When it is, the view moves with the
hero: the game keeps a *camera* on the map and slides it as you walk, so
every square stays the same size and stays readable. A map that fits is
shown whole; one that does not, scrolls.

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
