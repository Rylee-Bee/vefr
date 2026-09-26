# Brain roles: the smallest capable model for each job

A plan, agreed with the owner on 2026-09-26. Candidates below come from a
Hugging Face survey on that date (raw output:
[`docs/research/2026-09-26-huggingface-small-models.txt`](../research/2026-09-26-huggingface-small-models.txt)).
**None of them has been tested on our hardware yet**; the bake-off at the end
decides.

## The idea

VEFR's brain is **shared, not universal**: each job gets the smallest model
that does it well, instead of one big generalist. That keeps downloads small,
runs on ordinary CPUs (x86 and ARM), and lets any role be swapped.

- **Everything runs locally.** No role may require a cloud provider.
- **First run, you choose:** a curated profile (a template naming one model
  per role), or, role by role, any OpenAI-compatible provider you already use
  (Ollama, LM Studio, a cloud service).
- **Rules first.** Where rules do the job (sound effects, simple sprites,
  map checks), no model is used at all.
- **Games never need a model** (ADR 0003). These roles serve the studio.
- **Open weights, licences we can ship.** Apache-2.0 and MIT are preferred.
  Non-commercial licences (CC BY-NC) are excluded. "Other" licences are
  checked before bundling.

Runtimes: GGUF on llama.cpp for text and vision; whisper.cpp or ONNX for
speech; stable-diffusion.cpp for images.

## What we already measured

The owner's Small Model Olympics (`bench/olympics`, suite 0.4.1, 27 models,
53-task qualifier, 2026-09-13; summary in
`bench/reports/QUALIFIER-TLDR-2026-09-13.md`) is the evidence to start from:

- **Top:** qwen3-1.7b 76%, lfm2.5-2.6b 70%, ministral-3-3b 68%, falcon3-3b 66%.
- **Middle:** gemma3-4b, phi-3.5-mini, phi-4-mini 64%; granite-4.1-3b,
  qwen2.5-1.5b-tools, qwen2.5-3b 62%.
- **Weak:** gemma3-1b 42%; qwen3.5-0.8b and -2b 30% and 28% (the report notes
  a missing Q8_0 file and template fixes; retest before judging).
- The earlier model search (`.project/archive/model-benchmarks-2026-09/`)
  routed bounded tasks to Qwen2.5-1.5B (default) with Granite 4.1 3B as
  fallback; ADR 0002 picked Ministral 3 3B as storyteller.

Latencies in that campaign were measured on a contended GPU, so size and
speed still need re-measuring on a plain CPU.

## Candidates by role (Hugging Face, 2026-09-26)

Sizes are parameter counts; a 4-bit GGUF is roughly 0.6 GB per billion.

| Role | What it must do | Candidates | Licence |
|---|---|---|---|
| **Spark** (structured edits, routing, JSON) | Never break a schema; fast | Qwen3.5-0.8B · MiniCPM5-1B · LFM2.5-230M · Gemma 4 E2B (QAT q4 GGUF from Google) · LFM2.5-Encoder-350M-Prompt-Router (routing only) | Apache-2.0 · Apache-2.0 · other · Apache-2.0 · other |
| **Storyteller** (narration, dialogue) | Voice, continuity, character | MiniCPM5-2B (2026-09) · Ministral-3-3B-Instruct-2512 (ADR 0002's pick) · Granite 4.2 3B · Qwen3.5-4B · SmolLM3-3B · LFM2.5-2.6B | Apache-2.0 ×5 · other |
| **Names and flavour** | Short, creative, cheap | LFM2.5-230M · Qwen3.5-0.8B · Baguettotron (0.32B) | other · Apache-2.0 · Apache-2.0 |
| **Embeddings** (lore search) | Find the right lore | granite-embedding-97m-multilingual-r2 · granite-embedding-311m-multilingual-r2 · harrier-oss-v1-0.6b · Qwen3-Embedding-0.6B · EmbeddingGemma-300m | Apache-2.0 · Apache-2.0 · MIT · Apache-2.0 · Gemma terms |
| **Reranking** (optional) | Order search results | R3-rerank-0.6b (Tencent) | Apache-2.0 |
| **Vision** (look at art, screenshots) | Describe, tag, check | Qwen3.5-0.8B (also Spark) · MiniCPM-V-4.6 (1.3B) · Gemma 4 E2B · GLM-OCR (1.3B, text in images) | Apache-2.0 · Apache-2.0 · Apache-2.0 · MIT |
| **Image generation** | Sprites, tiles, art | Rules first (palette sprites). Then FLUX.2-klein-4B (slow on CPU: minutes per image) · SD-Turbo (0.87B, check terms) · pixel-art LoRAs | Apache-2.0 · check · varies |
| **Voice out** (text-to-speech) | Accessibility, character voices | Kitten TTS nano 0.8 · Kokoro-82M · Qwen3-TTS-0.6B (custom voices, heavier) | Apache-2.0 ×3 |
| **Voice in** (speech-to-text) | Talk to residents | Moonshine streaming tiny/small (0.04B/0.14B) · Granite speech 5.0 470M · Qwen3-ASR-0.6B · Parakeet TDT 0.6B v3 | MIT · Apache-2.0 · Apache-2.0 · CC BY 4.0 (attribution) |
| **Sound effects and music** | Bleeps, loops | Rules first (sfxr-style, trackers). Then Stable Audio 3 small sfx/music (0.57B) | none · Stability terms, check |
| **Translation** (optional) | Share games in other languages | Hy-MT2-1.8B (Tencent) | Apache-2.0 |
| **Safety check** (optional, for sharing) | Flag harmful text | Shieldstral-1.0-3B (Mistral) | Apache-2.0 |

What changed since the older bundled-brain design
([`bundled-brain.md`](bundled-brain.md)): Gemma 4 is Apache-2.0; small Qwen
models are now natively multimodal (one model can be Spark *and* vision);
MiniCPM5 and LFM2.5 are new; tiny speech models (Kitten, Moonshine
streaming) and a 97M multilingual embedder make a sub-1 GB profile realistic.

## Smaller labs worth testing

Trained and optimized small models from outside the big labs, from a second
survey the same day (raw output:
[`docs/research/2026-09-26-huggingface-smaller-labs.txt`](../research/2026-09-26-huggingface-smaller-labs.txt)).
Check each model's provenance and card before bundling.

| Role | Candidates | Licence |
|---|---|---|
| Storyteller / Spark | Nanbeige4.2-3B · VibeThinker-3B · HRM-Text-1B (new architecture) · NeoHorse-1-4B and Spark-X2.5-4B (very popular; verify provenance first) | Apache-2.0 · MIT · Apache-2.0 · Apache-2.0 |
| Embeddings | LightOn LateOn / DenseOn (0.15B) · bekko-embedding (0.11–0.12B) · pplx-embed-v1-late-0.6b | Apache-2.0 · MIT · MIT |
| Voice out | Audio8-TTS 0.1B / 0.6B · gepard-1.0 (0.56B) | other / Apache-2.0 · Apache-2.0 |
| Voice in | Fun-ASR-Nano (0.8B) | Apache-2.0 |
| Text in images | PaddleOCR-VL-1.6 (0.96B) · OvisOCR2 (0.85B) | Apache-2.0 ×2 |
| Image generation | none under 4B; rules first stays right | |

## Embedders instead of generators

Many "brain" jobs don't need to generate anything, and a 0.1–0.3B embedder
answers in milliseconds where a generator takes seconds. Use one wherever
comparing is enough:

- **Style check:** does a new sprite or picture match the approved house art?
  Compare image embeddings (microsoft/Mage-ViT, 0.32B, MIT; google/tipsv2-b14,
  0.2B, Apache-2.0) against the design system's pictures.
- **Art search and dedupe:** "find every lantern icon", "is this a near
  copy?".
- **Routing:** which resident or module handles a request, by similarity to
  labelled examples, instead of asking Spark.
- **Tagging and memory search:** lore, books and past sessions. Some of this
  needs no model at all: plain indexing, as in the deja-vu approach noted in
  the pickle repo's research.

## Fit to the machine

"The best with whatever the user has": on first run the studio looks at the
machine (memory, CPU cores and instruction set, any GPU, free disk) and
pre-selects the largest profile that fits comfortably, then shows what it
chose and why. Every role degrades gracefully: a smaller model, then rules,
then "not available on this machine" with the reason, never a crash. A
provider can be tied to any single role to lift it beyond the machine.

## Draft profiles (to confirm by the bake-off)

| Profile | Roles | Rough download |
|---|---|---|
| **Tiny** (any laptop) | Qwen3-1.7B (Spark and names; top of the olympics) · granite-embedding-97m · Kitten TTS nano · Moonshine tiny · rules for sprites and sound | about 1.5 GB |
| **Standard** | Tiny + a storyteller (Ministral 3 3B or LFM2.5-2.6B, both proven; MiniCPM5-2B to test) + vision (MiniCPM-V-4.6) · Kokoro · Moonshine small | about 4–5 GB |
| **Full** | Standard + image generation (FLUX.2-klein-4B) + translation (Hy-MT2) | about 7–8 GB |

Any role in any profile can point at a provider instead.

## The bake-off (next step)

The harness exists: add the new candidates as participants in
`bench/olympics` (MiniCPM5-1B/2B, Gemma 4 E2B, Nanbeige4.2-3B, LFM2.5-230M,
Granite 4.2 3B, SmolLM3-3B, and a Qwen3.5 retest), run the qualifier on a
plain CPU, and add role-specific checks the olympics doesn't cover yet:

- **Spark:** JSON-schema validity across a fixed set of studio edits; latency.
- **Storyteller:** the continuity cases from ADR 0002; voice and character
  separation; latency.
- **Embeddings:** retrieval accuracy on the sample world's lore.
- **Vision:** describing the studio's own art correctly.
- **Speech:** word error rate on a short script; real-time factor.
- **Every model:** file size, peak memory, tokens or audio seconds per second,
  licence confirmed from the model card.

Winners become the curated profiles; the results land in a new ADR.
