---
title: Money and Shops
kind: book
shelf: how-vefr-works
short: How gold, a shop, and using a carried thing work in a woven game.
source: src/vefr/cli.py
---
A fight now leaves something behind, and a thing you carry can have a
use. The last step is the reward end: a purse of gold, someone willing
to buy and sell, and a way to spend what you have. It is small by
design - no haggling, no stock to run out, no weight.

* * *

Gold is one number, kept for you and remembered between visits. A world
may start you with some in its `player` block, and the purse grows or
shrinks as you trade. It shows as a short line at the top of the screen
and as plain words in the pause menu's Bag panel. A world that has no
shop and nothing with a price shows no gold line at all, so an older
game looks exactly as it did.

* * *

Prices come from the world, not the engine. A thing can be given a
`value` in the world's `items` catalog, and that number is both what a
shop pays when you sell and what it asks when you buy. A healing thing
can also carry a `heal` and a `use` verb, so a potion is drunk and
bread is eaten.

* * *

A trader is just a person who has been marked as a shop. Stand beside
them and use the world's interact verb and a Trade panel opens. The
top list offers your carried things they will buy; the lower list
offers what they sell. Press a button to make the trade: the purse and
both lists move at once, and a line says what happened. If you cannot
afford something, its button is simply unavailable. Talking to them
still gives their own line; trading is a separate act.

* * *

A carried thing with a heal gets a Use button in the Bag panel. Using
it raises your health by its heal, up to your full health and no
further, and spends one copy. If you are already whole, it says so and
keeps the thing - a potion is never wasted on nothing.

* * *

**Try it.** In a world with a trader, walk up to them and open the
Trade panel. Sell something you no longer need, then spend the gold on
something you do.
