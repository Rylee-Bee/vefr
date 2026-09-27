---
title: Layers, Like Paper on Paper
kind: book
shelf: how-vefr-works
---
Paint a picture of a meadow. Now paint a fox on top. The fox covers a
bit of grass, and that's fine: the grass is still under there.

Games draw every picture this way, back to front, many times a second.
Each step is a *layer*. The order is the *draw order*, or *z-order*.

* * *

When the town is drawn, it goes in this order:

1. The dark behind everything (the *background*).
2. The ground, square by square (the *tile layer*).
3. Little marks on the ground: gold, reeds, waves (*decoration*).
4. The tower's watchful shadow (an *overlay*, see-through on purpose).
5. The people of the town (*sprites*).
6. The hero, last, so nothing hides them.

* * *

Change the order and the world looks wrong. Draw the ground after the
hero, and the hero vanishes under the grass.

Programmers call "draw back to front" the *painter's algorithm*,
because it's exactly what a painter does.

* * *

A see-through layer is *transparent*. Pictures keep a hidden fourth
colour called *alpha*: how much you can see through each dot.

That's why the residents' pictures have no box around them: the
empty parts are alpha zero, so the ground shows through.

* * *

**Try it.** Walk the hero into the tower's shadow. The ground gets a
little darker but you can still see it. That's the overlay layer, drawn
on top and partly see-through.

Now stand on a safe square. The shadow skips it: the game checks each
square before drawing that layer. Rules deciding what gets drawn is
most of what a *renderer* does.
