# Studio modules

A plan, agreed with the owner on 2026-09-26. The commission board
(below) is the first slice built; the rest is still plan.

VEFR is a whole game studio that publishes games in house. A **studio
module** is one small helper a game maker can slot into their studio to
make something their game needs: a sprite, a sound, a name, a book
draft. It does what a patient collaborator would do for them, packed
into a template, so the next time is easy and the result matches the
house style.

Two rules frame every module:

- **Models help in the studio; games are finished artifacts.** A module
  runs while a game is being made. What it makes is approved, then baked
  into the game. Games never depend on a model (ADR 0003).
- **Smallest capable model for every job.** Rules first, then the
  smallest model that does the job well, then bigger or cloud models
  only when the maker asks for them. Small and local keeps the studio
  free, private and fast on an ordinary computer.

## No money needed, ever

The studio must make whole games with **no paid service at all**: no
Claude, no cloud models, no subscriptions, no accounts. Templates,
rules and small local models carry every module. The `cloud` tier is an
optional extra a maker can switch on; nothing in the studio requires
it, and nothing is ever sold inside it (no purchases, no ads, no
currency to buy). Claude helped build the studio; the studio then runs
on its own.

## The studio is a game too

Making a game should feel as good as playing one: a fun, rewarding loop
that runs entirely inside the studio.

1. **A resident asks for something small.** A gentle commission, sized
   for one sitting: "Urðr would love a note for the Library", "The
   Cartographer needs a first floor". The maker can always ignore these
   and do their own thing.
2. **Make it** with a module: pick from a few options, tweak, keep.
3. **Try it** straight away in the playtest view.
4. **Keep it.** It lands in its room, and the resident reacts.
5. **The studio grows.** Rewards are warm and never block anything:
   - milestone stickers (first world, first book, first playtest, first
     share, first bug squashed);
   - the World Tree changes as the game grows: a lantern lights for each
     finished piece, and books appear in its branches;
   - a shelf in the Hall of every game the studio has published.
6. **Share it.** Publishing a finished game is the biggest milestone of
   all, and the next commission waits for tomorrow.

Rewards never lock features away: every module is available from the
start. They celebrate progress; they don't gate it.

## Built: the commission board (first slice)

Built 2026-09-29. The first piece of the loop is real, in the Hall:

- The **commission board** reads the current pack and shows one card
  per module.
- A commission is a **rule over the pack**, never a model call.
  The Cartographer asks for the town's first places: a path, a wall,
  and at least three kinds of ground with one marked as a place to
  walk to. Every mark the rule wants, the Map Room can paint.
- **Open the Map Room** takes the maker to the room that does the work.
- **Not now** defers a commission; the board remembers, and a deferred
  job simply waits. A job the pack already satisfies reads **done**.
- Everything else here is still plan: the other modules, the learning
  ladder, the spare parts shelf, and the Archives' two lists.

## Who it's for

Anyone who wants to make a small game, whatever they bring. People have
two separate skills, in any mix:

| | Tells a story | Wants help with the story |
|---|---|---|
| **Not technical** | The studio handles the machinery; they write | The most hand-holding: gentle story questions and simple taps |
| **Technical** | Sees and tweaks the wiring; writes their own story | Comfortable with the code; the residents help them find a story |

So the studio asks two questions the first time it opens, and both can
be changed any time in the Boiler Room, like the other preferences:

> **How much of the workings do you want to see?**
> Keep it simple · Show me how things work
>
> **How would you like to write your story?**
> I'll write it myself · Help me find it

- **Keep it simple** (the default): no words like "model", "prompt" or
  "folder" on screen. Residents speak for the modules ("The Keeper of
  Faces drew four cats. Which one belongs in your game?").
- **Show me how things work**: every module adds a "see how this works"
  view: the template it filled, the model or rule it used, the files it
  wrote, and the command-line equivalent. For learning and tweaking.
- **I'll write it myself** (the default): story modules stay out of the
  way. Residents may still offer small suggestions when asked.
- **Help me find it**: story modules switch on. The Storyteller asks
  questions ("Who is lonely in this town? What do they want?") and
  offers shapes from the Library's handbook (beginnings, turns,
  endings). The person chooses and writes; residents only offer, and
  nothing is kept without their say.

Story help is never automatic, and a maker's own story is never written
for them.

## Learn by making: the ladder

Rylee's dream for the studio: that people who play VEFR "can actually like... learn to be software
devs, but it be fun". The "Show me how things work" slider grows from two steps into a ladder. Each rung
shows one more real layer of the same thing, with a resident as the mentor, and ends with a sticker.
Nothing is simulated: every rung uses the studio's real files and real commands, so what you learn
works outside VEFR too.

| Rung | What you see | Mentor | The real skill |
|---|---|---|---|
| 1. Pictures | Paint the map, pick tiles, keep or redo | the Cartographer | using a tool well |
| 2. The data | The squares are symbols in a text file | the Cartographer | data and formats |
| 3. The files | A world's own files: a book, a character, the map | Fróði | reading and editing files |
| 4. The checks | Break the map on purpose; the checker catches it; fix it | Skuld | debugging and testing |
| 5. The history | Save a version, try something wild, go back | Urðr | version control |
| 6. The commands | The same buttons, typed (`ratatoskr weave` makes your game) | Ratatoskr | the command line |
| 7. Your own rule | Change one small rule of the game and see it play differently | Völundr | programming |

Rules for the ladder:

- **Opt in, one rung at a time.** "Keep it simple" stays the default; nobody is marched up.
- **Every quest uses the person's own world,** so the lesson is about something they care about.
- **Break things safely.** Each quest starts from a saved version and can always be undone.
- **Playtest on Cottage of the Breeze first, with Rylee as the first player.** A rung is ready when it
  makes something click; confusion or boredom is the bug to fix.
- **The residents are the dev roles in costume:** the Cartographer (level design), Skuld (tests and
  truth), Urðr (version history), Völundr (settings and ops), Ratatoskr (shipping), Fróði (files and
  docs). The handbook's seven stages are the real process software follows.

## What every module declares

| Part | What it is |
|---|---|
| **Name and resident** | What it makes, and which resident speaks for it |
| **Template** | The know-how: style bible, sizes, palettes, voice, examples |
| **Model tier** | `rules` (no model), `tiny` (under 1B), `small` (about 3–4B, like Spark), or `cloud` (only on request) |
| **Choosing** | How options are shown (usually a few to pick from) and how approval works. Nothing is final until the maker picks it |
| **Home** | Where approved work lands: the world pack's folders, the Vault, the Library |
| **See how this works** | What the technical view shows |
| **Offline fallback** | What happens with no model: rules, saved examples, or writing it by hand |

## First modules

Rules first, then tiny models, so the first ones work on any computer:

| Module | Makes | Tier | Speaks for it |
|---|---|---|---|
| **Pixel sprites** | 16×16 and 32×32 sprites and tiles in a fixed palette | `rules` | The Keeper of Faces |
| **Sound bleeps** | Retro sound effects (steps, doors, coins, hits) | `rules` | Völundr |
| **Names and flavour** | Names for people, places and items; short item descriptions | `tiny` | The Hoard-Keeper |
| **Book drafts** | First drafts of in-world books and notes, from the maker's outline | `small` | Urðr |
| **Map sketches** | Floor and town layouts that pass the map checker | `rules` + `small` | The Cartographer |
| **Story questions** | Questions and handbook shapes, for "Help me find it" | `small` | The Storyteller |
| **Big art** | Portraits, title art, posters | `cloud`, on request | The Keeper of Faces |

The first to build is **Pixel sprites**: it needs no model, and it
paints the town and the dungeon floors.

## Where today's workflows go

These were done by hand with the owner on 2026-09-26 and become
templates:

- The art wish list and its prompt recipe (style bible, reference
  images, negative prompt, flat background, cut-out) → **Big art**.
- The plain-language rules → a checker that suggests fixes to studio
  text before it ships.
- The status timeline → Ratatoskr adds a stop after each milestone.
- The VEFR Studio design system → the shared style every module reads.
