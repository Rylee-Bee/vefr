# Historical event - copy-paste prompt

Use this prompt with any LLM (Claude, ChatGPT, your local
llama.cpp, whatever you prefer) to do the *real* research pass
before building a historical-event-flavored world. The engine's
`/api/lore/preview` endpoint wraps this in a one-shot call, but
you can also paste it manually.

---

You're a research assistant helping me build a playable world
shaped around a real historical event. The world is **what the
record couldn't hold** - the silence, the name the family used at
home, the thing the witness saw and didn't write down.

This isn't about recreating the event. It's about the world that
*grew up next to* the event and learned to live with it.

Here's what I'm working from:

[PASTE YOUR EVENT, SETTING, OR EXISTING IDEAS HERE]

[example: "the SS Mendi, 1918 - the South African labour corps
ship that sank in the English Channel after being struck in fog.
Most of the dead were Black South African men; the survivors
were white British crew."]
[example: "a shtetl, 1942 - the year the people stopped coming back"]
[example: "the Kindertransport, 1938-1939 - the children who went"]

## What I want back

### 1. Three textures (2-4 paragraphs each)
A "texture" is the feel of a thing - what it sounds like, smells
like, who walks through it, what they do when no one's looking.

Pick three of these and write one paragraph each:

- a **place** the player will walk through (the kitchen where
  the news arrived, the road out, the room that stays shut)
- a **person** the player will talk to (someone who was there,
  someone who came back, someone who never talked about it)
- a **moment** the world keeps asking the player to come back to

Don't try to be complete. Try to be *felt*. The point isn't to
build the world - it's to give me words that make me want to.

### 2. A handful of names (5-10)
In this flavor, names have layers: the public name (in the
record), the home name (in the family), and the place name (on
the street). For each name, give:

- the **name** itself (or one of its layers)
- one sentence on **what it sounds like** when someone says it
- one sentence on **what it belongs to**

If a real person's name surfaces in your research, **do not put it
in your answer**. Use place names and roles instead ("the
captain," "the witness from the south pier"). Real people deserve
their own names. Your answer is for the world, not the record.

### 3. The questions I'd ask you next
Write 2-4 questions - the ones that make me realize the world has
depths I haven't seen yet. These should feel like they come from
the world itself, not from a research outline.

## What I don't want

- A history lesson. I can read Wikipedia.
- A retelling of the event. The world is *adjacent*, not the event.
- A list of names of real people who died or suffered.
- Anything that uses real names as characters.
- Anything that sounds like "now you can experience what they
  experienced." No. The world is *how the town lives with what
  it remembers*, not a simulation of the event.

## Tone rules

- **Show, don't explain.** A texture is *what you see when you
  walk in*, not *what the town is for*.
- **The record is right, the world is what the record left out.**
  When in doubt, choose the kitchen over the archive.
- **Witnesses are not heroes.** They are people who saw something
  and then lived with having seen it.
- **Roadside prose, not library prose.** Brevity over completeness.
  A little crooked over polished.
- **Never use a real person's name.** Not even in the textures.
  Place names, roles, kinds. The real names belong to the real
  people.

## Sources

For the *real* research, source public-domain archives:
- Project Gutenberg (gutenberg.org) - public domain texts
- The Internet Archive (archive.org) - public-domain collections
- Government archives (national archives are usually public-domain
  for older materials)
- University libraries (many have public-domain digital collections)

For the *texture*, you don't need sources. You need **listening**.
Talk to people who lived through similar events. Read first-person
accounts. Sit with what they wrote.

---

When you're done, I'll use what you wrote as the seed-textures
that `norns craft chat` reads when it interviews me. The chat
will then ask its own questions about colors, feelings, named
figures - the things your research *can't* decide.