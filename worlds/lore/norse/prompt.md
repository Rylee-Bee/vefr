# Norse wandering poets - copy-paste prompt

Use this prompt with any LLM (Claude, ChatGPT, your local llama.cpp,
whatever you prefer) to do the *real* research pass before building
a Norse world. The engine's `/api/lore/preview` endpoint wraps this
in a one-shot call, but you can also paste it manually.

---

You're a research assistant helping me build a playable world with a
Norse flavor. The world will be shaped like the journey-poetry of
the wandering poets: skalds, smiths, travelers, names with weight,
verse in place of record. I don't want a textbook. I want the
texture of someone telling me a story by the fire.

Here's what I'm working from:

[PASTE YOUR SEED WORDS, MOOD, OR EXISTING IDEAS HERE]

[example: "the Mendi crisis, 1918 but recast in skald-verse"]
[example: "a bookshop at the edge of a town that forgets itself"]
[example: "I want the keeper of a bell to remember something no one else does"]

## What I want back

### 1. Three textures (2-4 paragraphs each)
A "texture" is the feel of a thing - what it sounds like, smells
like, who walks through it, what they do when no one's looking.
Pick three of these and write one paragraph each:

- a **place** the player will walk through (a town, a road, a
  hall, a market, a forge, whatever feels right)
- a **person** the player will talk to (someone the skalds
  have sung about, or someone the skalds have forgotten)
- a **moment** the world keeps asking the player to come back to
  (the bell rings, the stranger arrives, the river is high)

Don't try to be complete. Try to be *felt*. The point isn't to
build the world - it's to give me words that make me want to.

### 2. A handful of names (5-10)
Names carry weight in this flavor. Some can be kennings (compound
poetic names), some can be proper names from the Eddas or sagas,
some can be invented. For each name, give:

- the **name itself**
- one sentence on **what it sounds like** when someone says it
- one sentence on **what it belongs to**

### 3. The questions I'd ask you next
The world has things it wants me to know about it. Write 2-4
questions - not the obvious ones ("what's the central conflict?")
but the ones that make me realize the world has depths I haven't
seen yet.

## What I don't want

- A summary of Norse mythology.
- A worldbuilding template with sections to fill in.
- Lists of gods and their domains.
- Anything that smells like "here are the ten things your Norse
  world needs."

## Tone rules

- **Show, don't explain.** A texture is *what you see when you
  walk in*, not *what the town is for*.
- **Names are weight, not labels.** When you name a thing, say
  what it does to the person naming it.
- **Verse in place of record.** If a fact and a song disagree,
  the song wins. I want the world's law to be what the skalds
  agree on, not what's true.
- **Roadside prose, not library prose.** Brevity over completeness.
  A little crooked over polished.

---

When you're done, I'll use what you wrote as the seed-textures
that `norns craft chat` reads when it interviews me. The chat
will then ask its own questions about colors, feelings, named
figures - the things your research *can't* decide.