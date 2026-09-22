# Storyteller Packs

A storyteller is the voice VEFR invites into the world.

VEFR keeps the facts: where everyone is, what they know, what
happened, what the player is carrying, and which mysteries are still
unresolved. The storyteller doesn't need to hold the whole world in
its head. VEFR gives it the small piece of the story that matters
right now and asks it to imagine what happens next.

A Storyteller Pack teaches VEFR how to work with a particular
language model. It can describe the model, its capabilities, its
preferred generation settings, and the templates that shape the
conversation.

**The model is replaceable. The world is not.**

---

## The short version

```text
VEFR owns the world.
The harness prepares the moment.
The storyteller imagines the response.
```

### VEFR owns the world

VEFR is authoritative for canon, state, locations, characters,
relationships, inventory, mechanics, history, and what each
character actually knows. The model does not get to make something
true merely by saying it. If the engine knows the door is locked,
the door is locked, no matter how a storyteller narrates it.

### The harness prepares the moment

VEFR selects the relevant slice of the world and turns it into a
compact scene packet. The storyteller should not need the entire
save file, the whole map, every journal entry, and the entire lore
library to answer one line of dialogue.

This is an important design principle called **minimum sufficient
story context**: a packet should contain exactly enough world truth
to answer the question at hand, and nothing that would tempt the
model to leak canon the character can't know.

### The storyteller imagines the response

The model contributes dialogue, prose, reactions, emotional texture,
interpretation, connective tissue, surprises, and possible story
beats. Its job is imagination, not database administration.

---

## Storytellers are game assets

VEFR treats its recommended storyteller much like another game
asset. The mental companions are things like a font, a shader, a
tileset, a sound pack. A storyteller gives the game its voice; swap
it, the voice changes; the world does not.

A VEFR install may eventually offer a recommended lightweight
storyteller so someone can simply install the game and play, the
same way most games ship with a default font or default music.

A recommended storyteller is a known-good starting point. It is not
a requirement. Users should be free to bring another model, a
hosted endpoint, or a fine-tune their friend made.

---

## Bring your own model

Already have a model you love? Use it.

VEFR's storyteller boundary is intentionally model-neutral. A player
might use the lightweight storyteller recommended by VEFR, a strange
little roleplay fine-tune, a larger model running on another
machine, or a hosted endpoint. VEFR still owns the world either way.

The engine speaks two wire protocols natively:

| Protocol | Used by | Notes |
|---|---|---|
| `openai-compatible` | llama.cpp's server, LM Studio local server, vLLM, LocalAI, text-generation-inference, OpenRouter | Anything that exposes `/v1/chat/completions`. One code path, many runtimes. |
| `ollama` | Ollama's local server | Uses `/api/generate`. Separate path so ollama-native fields stay where they belong. |

To point VEFR at a specific model without writing a pack, set the
environment variable:

```sh
export VEFR_STORYTELLER=my-model-name
```

If that model has an installed pack, VEFR uses the pack. If not, VEFR
treats it as a bring-your-own-model placeholder so the game still
boots. Run a backend, drop the model name in the env, and play.

---

## Capability tiers

Every Storyteller Pack declares what the model can do. The current
implementation tracks four flags and derives a tier from them:

| Capability flag | What it means |
|---|---|
| `text` | Plain text generation. Required. |
| `structured_output` | Can return JSON proposals / metadata when asked. |
| `tools` | Supports native tool/function calling. |
| `vision` | Accepts image input (reserved; no game path uses this yet). |

The derived tiers, smallest to largest:

### Storyteller

Plain text generation. This is the important minimum. If a model
can read a scene packet and answer with text, it can sit at the
table.

VEFR's Tier 1 caller (`generator.storytell()`) talks only to
storyteller-tier models. It never asks for JSON, never asks for
tools. That is deliberate: it means a creative 2B model with no
agent features is still a perfectly valid VEFR storyteller.

### Structured storyteller

Can additionally return structured information where supported. Some
engine surfaces (rumors, NPC lines, lore previews, stefna letters)
parse JSON Schema responses for richer data; a structured pack is
asked for those.

### Agentic storyteller / helper

Supports native tool/function calling. Useful for richer player
help and future engine surfaces that want to let the model inspect
state. Not required for basic storytelling.

Tier 3 is also where the engine's existing `gpt-oss-20b`
integration lives, used for proposal generation and player help.

The capability flags belong to the pack, not the engine. A pack
author who knows their model can't do JSON leaves
`structured_output = false` and the engine never asks.

---

## Small models are first-class

VEFR is deliberately interested in small storytellers.

A dedicated GPU should make local storytelling faster or richer. It
should not be the price of admission. Someone with an ordinary
laptop should be able to install VEFR, install a lightweight
storyteller, and play.

The harness therefore assumes:

- inference may be slow
- context should be carefully selected
- output may be short
- sophisticated reasoning may not exist
- tools may not exist
- the model should not be responsible for remembering the whole world

> **Let the little model spend its limited attention on being a person.**

That is the design goal. A 2B model that stays coherent inside a
VEFR scene because the harness prepared excellent context is a
success, not a compromise. The same scene packet sent to a 12B
reference model should read like a different voice at the same
table, not a different game.

---

## What goes in a Storyteller Pack

A pack is one directory. Inside it sits one TOML manifest and,
optionally, the markdown templates that the manifest names.

### File layout

```text
storytellers/
  <pack-id>/
    storyteller.toml      # required - the manifest
    system.md             # optional - system role template
    scene.md              # optional - scene packet wrapper
    character.md          # optional - reserved for Tier 2/3
    memory.md             # optional - reserved for Tier 2/3
```

The manifest is the only file VEFR must parse. Templates are loaded
only if referenced and present. A pack that ships zero model data
and zero templates is still valid; it just hands whatever prompt the
caller supplies to whatever model the player has.

The manifest filename is **`storyteller.toml`**. Bundled packs ship
under `storyteller_packs/` at the repo root; per-machine installs
land under `data/storytellers/` (gitignored).

### File-type convention

The current convention is plain:

- **TOML** for human-authored manifests and configuration
- **Markdown / text** for authored storytelling templates
- **JSON** for machine-facing state, fixtures, and API interchange

Packs do not need to invent a fourth format. A pack author who wants
their templates in a different layout can ship them; the manifest's
`[templates]` block names the exact filenames.

### Minimal working manifest

The smallest meaningful pack looks like this:

```toml
[storyteller]
id = "my-tiny-storyteller"
name = "My Tiny Storyteller"
version = "0.1.0"

[model]
provider = "openai-compatible"
model = "my-model-name"

[capabilities]
text = true
```

That is enough to register a pack with VEFR. Three blocks, ten lines,
the engine can resolve it.

### Full annotated manifest

Here is what every field actually means, against the dataclasses in
`src/vefr/storyteller.py`:

```toml
# Who the pack is.
[storyteller]
id = "gemma4-e2b"           # unique id; used as VEFR_STORYTELLER value
name = "Gemma 4 E2B"        # display name
version = "0.1.0"           # free-form, helps humans track updates

# Which model and which wire protocol.
[model]
provider = "openai-compatible"   # "openai-compatible" or "ollama"
model = "gemma-4-E2B-it"        # model name the backend expects
source = "huggingface"          # provenance hint, free-form
context_window = 131072         # 0 = unknown; informational

# What the model can do. Tier derives from these flags.
[capabilities]
text = true                    # required
structured_output = false       # JSON / Schema responses
tools = false                   # native function calling
vision = false                  # image input (reserved)

# Generation settings. The harness respects these by default.
[sampling]
temperature = 0.8
top_p = 0.9
top_k = 64

# Provider-specific chat template hints.
# gpt-oss uses reasoning_effort; Gemma 4 uses thinking tokens;
# most models leave this empty.
[chat_template_kwargs]
# reasoning_effort = "low"

# Optional. Files are relative to the pack directory.
# Each defaults to "<kind>.md" at the pack root if unset.
[templates]
system = "system.md"
scene = "scene.md"
character = "character.md"
memory = "memory.md"

# Required. Where did the weights come from, and what are the terms?
[license]
name = "Gemma 4 (Google DeepMind)"
spdx = "Apache-2.0"
source_url = "https://huggingface.co/google/gemma-4-E2B"
redistribution = "allowed"
commercial_use = "allowed"
attribution = "Gemma 4 E2B by Google DeepMind, Apache-2.0"
notes = "Gemma Terms of Use apply; see upstream license page."

# Optional. Only useful if the pack wants to point the player
# at a specific artifact to fetch.
[install]
weights_source = "huggingface"
weights_repo = "google/gemma-4-E2B-it"
recommended_quant = "Q4_K_M"
approx_disk_mb = 2700
fetch_command = "# ollama pull gemma-4-e2b  OR  llama.cpp from HF"
attribution_url = "https://huggingface.co/google/gemma-4-E2B"
notes = "Approx disk estimate for Q4_K_M GGUF."

[notes]
text = "Free-form author notes. Lives in a sub-table to avoid TOML ambiguity."
```

Unknown top-level fields are ignored. Forward compatibility is
deliberate: the engine should keep loading packs written by older
or future versions of itself.

---

## Anatomy of a scene

The harness's job is one struct: a `ScenePacket`. It is what the
model sees. Below is the bundled sample fixture from
`tests/fixtures/storyteller/sample-scene.json`, rendered into
the packet shape the storyteller actually receives:

```text
WHO YOU ARE

The forge's caretaker.

You tend the bell, the tools, and the door.
You have worked here long enough to notice what does not belong.
You answer plainly and stop talking before you fill the silence.

WHAT YOU KNOW

The bell rang once after the forge went cold.
No delivery was due last night.

WHAT YOU DO NOT KNOW

You do NOT know who left the sealed letter by the door.

CURRENT SCENE

The forge is cold.
Tools hang in a clean row on the wall.
The street outside has gone quiet.
One oil lamp still burns by the door.

RELATIONSHIP

The player returned a lost tool yesterday.

WHAT JUST HAPPENED

The player asked:

"Who rang the bell after the forge went cold?"

OPEN THREADS

A sealed letter is waiting by the door.
The morning delivery has not come.

WRITE

Respond naturally. Include your immediate physical behavior if useful. Do not reveal facts you cannot know. Do not resolve every mystery. Leave room for the player to continue.
```

Notice the **`WHAT YOU KNOW`** and **`WHAT YOU DO NOT KNOW`**
sections. They are separate on purpose.

> **VEFR may know something the speaker does not.**

The sealed letter is canon. It exists in world state. The caretaker
has no business knowing who left it. The packet encodes the boundary
explicitly so a small model can stay in character even when its
training data contains plausible conspiracy tropes. If the packet
didn't draw the line, the model would.

This is one of the major reasons VEFR prepares context instead of
handing the model the whole world. The packet is the epistemic
contract for one scene.

A fixture is data, not code. Adding a new scene means adding a new
JSON file. The harness reads whatever fixture the CLI names,
searching `VEFR_STORYTELLER_FIXTURES` first (a PATH-style list of
directories) and then the engine's own `tests/fixtures/storyteller/`.
A pack keeps its scenes in its own repo and points the variable at
them - fixture content follows ownership.

---

## Writing a good storyteller template

These are observations from the current implementation, not
universal rules.

### Give the model a role

Tell it who it is or what narrative function it is performing.
"Respond as the caretaker" is more useful than "respond helpfully."
Voice
comes from the role, not from temperature settings.

### Give it facts, not a data dump

A handful of relevant facts beats a paragraph of everything you
could say about the world. The pack author is in charge of the
template; keep it short.

### Separate world truth from character knowledge

Use the packet's `speaker_knows` / `speaker_does_not_know`
split. Encode the boundary in plain language. Models obey plain
language more reliably than they obey complex instructions about
"don't mention things the character wouldn't know."

### Tell it what just happened

The player's most recent action should be unambiguous in the
packet. The harness already puts it in `recent_action`; the
template should not bury it under other context.

### Leave space

Do not ask the model to resolve the scene. The player needs
somewhere to go next. End the packet with an instruction like
"respond in voice; leave room for the player to continue." A
model trained on web prose otherwise tends to write a satisfying
conclusion.

### Prefer short generations

A few excellent lines can be more useful in a game than seven
hundred words of competent prose. The audition harness defaults to
`max_tokens = 180`; pack authors who want longer output say so
explicitly.

### Don't make prose models do engine work

If VEFR already knows whether a door is locked, whether an NPC is
in the room, or whether the player has the right key, give the
model those facts. Don't ask it to figure them out. **Let the
little model spend its limited attention on being a person.**

---

## The storyteller audition

Reading prose is the test. VEFR ships a small harness so you can
run the same scene through multiple storytellers and put the
results side by side.

### What it is

> This is an audition, not a leaderboard.

The harness sends the same `ScenePacket` to each configured
storyteller, captures the responses, writes them to disk, and
prints a skim-friendly summary to the terminal. There are no
automatic scores and no benchmark leaderboard. You read the prose
and decide.

### How to run it

```sh
# every configured storyteller, three runs each
uv run norns storyteller-test --matrix --runs 3

# one specific storyteller
uv run norns storyteller-test --model gemma4-e2b

# a different scene fixture (default: sample-scene)
uv run norns storyteller-test --matrix --scene <fixture-id>

# blind mode: outputs labelled Storyteller A/B/C, mapping written to blind_map.txt
uv run norns storyteller-test --matrix --blind
```

The full help text:

```text
usage: norns storyteller-test [-h] [--model MODEL] [--matrix] [--scene SCENE]
                              [--runs RUNS] [--seed SEED] [--blind]

options:
  -h, --help     show this help message and exit
  --model MODEL  pack id or model name to run (mutually exclusive with
                 --matrix)
  --matrix       run the scene through every installed pack
  --scene SCENE  scene fixture id (default: sample-scene)
  --runs RUNS    repetitions per pack (default: 1; 3 recommended for creative
                 models)
  --seed SEED    record a seed for reproducibility (informational; providers
                 that support it will)
  --blind        label outputs Storyteller A/B/C and write a blind_map.txt for
                 later reveal
```

### What it writes

Each run creates a timestamped directory:

```text
artifacts/storyteller-tests/<timestamp>/
    manifest.json    # every result, structured: pack, model, scene, run,
                     # latency, sampling, license, response, status
    <pack-id>.txt    # one file per pack: prose across all runs
    blind_map.txt    # only when --blind was used
```

### What it doesn't do

- It does not score responses.
- It does not rank models.
- It does not select a winner.

If a model is not loaded on the backend, the run is marked
`SKIPPED - model not found` and the matrix continues. A skipped
model is not a harness failure.

Latency is always recorded. Token counts are recorded when the
backend reports them; small local backends don't always. That's
fine.

---

## How to judge an audition

Skip the benchmarks. Sit with the prose.

Questions worth asking:

- Does the character sound like someone?
- Does the response respect what the character knows?
- Does it react to what the player actually did?
- Does it contradict canon?
- Does it leave room for another action?
- Is there emotional texture?
- Is it interesting without becoming random?
- Does it sound like generic assistant prose?
- Do I want to answer?

That last one is the only one that matters for the question
VEFR is trying to answer.

> **The smallest model that makes you want to answer is more interesting to VEFR than the largest model that wins a benchmark.**

---

## Finding the cliff

VEFR is running an experiment. We test models of different sizes
against the same scene on purpose:

```text
large creative reference
        ↓
small storyteller
        ↓
tiny storyteller
        ↓
???
```

We're looking for the point where:

- voice disappears
- canon obedience breaks
- characters become generic
- player actions are misunderstood
- continuity stops working

We call this the **storytelling cliff**.

Why bother? Every time the harness lets a smaller model remain
coherent, more of VEFR's storytelling ability belongs to the engine
rather than to expensive hardware. That's the whole point of the
harness.

The cliff lives somewhere; we don't yet know where. The audition
harness is how we find it. No minimum model size is declared
because nothing has earned the right to declare it yet.

---

## Licensing

A model can be technically excellent and still be inappropriate as
VEFR's recommended download.

A Storyteller Pack records licensing and source metadata in the
`[license]` block: name, SPDX identifier where applicable, source
URL, redistribution status, commercial-use status, attribution
line, and any free-form notes.

Model selection should consider:

- redistribution rights
- commercial-use terms
- attribution requirements
- derivative restrictions
- whether automatic download is allowed
- whether weights can be mirrored or must be fetched upstream

Open weights do not automatically mean unrestricted redistribution.
Read the upstream license for any candidate you intend to recommend.

> **evaluation candidate ≠ distributable default**

Some models are perfectly fine to audition and never fine to bundle
as the recommended storyteller. A model whose license prohibits
commercial use, or requires flow-down of restrictive terms, can stay
in the harness as an evaluation candidate without ever becoming
VEFR's bundled default.

This document is not legal advice.

---

## Making your own pack

The shortest possible recipe, against the current implementation:

1. Copy the smallest existing pack that matches what you want.
   `storyteller_packs/gemma4-e2b/` is the thinnest example.
2. Give the pack a unique `id` in `[storyteller]` and a `name`.
3. Set `[model].provider` to either `openai-compatible` or
   `ollama`. Set `[model].model` to the exact name your backend
   expects.
4. Set `[capabilities]` flags to **only** what the model actually
   supports. Leave `structured_output` and `tools` off unless you
   have verified them.
5. Adjust `[templates]` only if you need different prompt
   framing. Defaults are `system.md`, `scene.md`, `character.md`,
   `memory.md` at the pack root.
6. Set conservative sampling in `[sampling]`. `temperature = 0.8`
   and `top_p = 0.9` are a fair starting point for creative
   prose.
7. Drop your pack under `data/storytellers/<id>/` (or
   `storyteller_packs/<id>/` if you're contributing to the engine).
8. Run the audition:
   ```sh
   uv run norns storyteller-test --model <your-pack-id> --runs 3
   ```
9. Read the output under
   `artifacts/storyteller-tests/<timestamp>/<your-pack-id>.txt`.
10. Change one thing at a time. Run it again.

> **Weird models are welcome.**

Fine-tunes, roleplay adapters, edge models, family-shifted oddities,
slow but charming models on old laptops: all are welcome. The
provider boundary only requires that the runtime speaks
`/v1/chat/completions` (or ollama's `/api/generate`); everything
beyond that is yours to play with.

---

## What not to put in a pack

A Storyteller Pack should not contain game-specific secrets merely
because it was developed against one game.

Examples of things that **do not belong in a generic pack**:

- character names from any specific game
- plot points from any specific game
- hidden canon the storyteller should know
- lore entries unique to one world
- sample-world-specific defaults

Those belong to the world pack, not to the storyteller pack.

VEFR enforces this with a pack-neutrality test that scans shipped
surfaces for known canon strings and fails the gate if any leak.
That test has already caught one stray docstring in the provider
implementation.

The rule is simple:

> **The pack teaches a model how to tell. The world tells it what is true.**

---

## Current reference packs

The repository ships six packs today. Five are bundled reference
packs under `storyteller_packs/`; one is an evaluation-only pack
under `data/storytellers/`.

### Bundled reference packs

| Pack ID | Model | Purpose | Tier | Status |
|---|---|---|---|---|
| `gpt-oss-20b-reference` | `gpt-oss-20b` | Smart control. The model the engine used to hardcode before the storyteller boundary landed. Tools + structured output. | 3 (agentic) | Bundled reference. Default for installs with no pack selected. |
| `gryphe-style-gemma-12b` | `gemma-4-12b-styletune` | Creative quality reference. Gryphe's `lm_head`-only style tune on Gemma 4 12B. Tier 1 only; engine never asks for JSON. | 1 (storyteller) | Bundled reference. Install-only; upstream license terms pending verification. |
| `gemma4-e2b` | `gemma-4-E2B-it` | Tier 0 audition candidate. 2.3B effective, edge-class. | 1 (storyteller) | Bundled audition candidate. |
| `gemma4-e4b` | `gemma-4-E4B-it` | Tier 1 audition candidate. 4.5B effective, same family as `gemma4-e2b`. | 1 (storyteller) | Bundled audition candidate. |
| `ministral3-3b` | `Ministral-3-3B-Instruct-2512` | Tiny Apache-2.0 audition candidate. Clean license, no Gemma-style additional terms. | 1 (storyteller) | Bundled audition candidate. |

### Evaluation-only packs

| Pack ID | Model | Purpose | Tier | Status |
|---|---|---|---|---|
| `qwen25-3b` | `Qwen2.5-3B-Instruct` | Tiny capability reference. Research-only license. | 1 (storyteller) | **Evaluation only.** Lives under `data/storytellers/`, not bundled. Never a shippable default. |

The audition harness runs every installed pack, bundled or
evaluation-only. The bundled/eval distinction only controls whether
the engine will *recommend* the pack; it does not restrict who is
allowed to audition one.

---

## Closing

VEFR does not need every storyteller to be brilliant at everything.

One may write beautiful dialogue. Another may be excellent at tools.
Another may run slowly on an old laptop and still give a character
one good line at exactly the right moment. The engine keeps the
world coherent. The harness prepares the moment. The storyteller
gets to imagine.

That's enough to begin.

### Where to read more

| Document | Path |
|---|---|
| Storyteller provider implementation | `src/vefr/storyteller.py` |
| Wire layer (completion routing) | `src/vefr/generator.py` |
| Audition harness | `src/vefr/storyteller_test.py` |
| Bundled packs | `storyteller_packs/` |
| Bundled sample fixture | `tests/fixtures/storyteller/sample-scene.json` |
| Test suite for the provider + harness | `tests/test_storyteller_test.py` |
