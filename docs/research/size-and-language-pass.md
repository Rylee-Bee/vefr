# Smaller and more flexible: a measured pass (2026-10-04)

Asked by Rylee: find places where VEFR can get smaller but more flexible, looking especially at how a different use of *language* can buy flexibility without costing human or agent readability. Everything below was measured on the shipped Cottage pack and the engine at `6395276`; nothing is built. Contract changes are ask-first.

## The one number that matters
The woven Cottage game is **3.34 MB**. **85% of it (2.85 MB) is base64 pictures.** The engine template is 284 KB (8.5%). The pack's own text is tiny: `world.json` 16 KB, `blueprint.json` 17 KB, the region files 37 KB, all books 3 KB, about 58 KB in total. So "smaller" is mostly a picture question; "more flexible" is mostly a language question. They are separate wins.

## A. Smaller: the bytes (measured)
| Lever | Measured | Effect |
|---|---|---|
| A1. Pictures baked as WebP, not PNG | 38 sprites: 1,209 KB PNG -> 286 KB lossy WebP (q88, -76%) or 834 KB lossless (-31%). The walk sheet: 312 KB -> 86 KB. | Woven file about 3.34 MB -> about 1.7 MB (-49%) with lossy; about 2.7 MB lossless. |
| A2. Identical pictures stored once | 11 region tile pictures, 6 unique: 208 KB -> 127 KB. The same deep tile is baked once per floor. | -80 KB. |
| A3. Bake only what is used | Not yet measured: sprites no rule, item, enemy or sheet names. | Probably small; measure first. |
Best place for A1: at *import* (the art-import verb, finding 6 of the discovery record), so the pack stores the small file and weaving stays byte-for-byte deterministic (an encoder upgrade would otherwise change every weave). Edge quality of cut-out sprites needs one look before lossy is the default; lossless is the safe floor.

## B. More flexible, no less readable: say it the way people say it
The pattern already exists and works: **Blueprint**. Authors edit a short source; `vefr normalize` expands it to the canonical form that is checked in and read-only; a lock catches drift; deleting the source is the exit ramp. The same move fits more places:
- **B1. Convention over listing.** 36 of Cottage's 38 `player.sprites` entries say exactly `"key": "sprites/key.png"`. If the file is there, the key exists. An item's `sprite` defaults to its id (7 of 14 already match). Fewer places to forget, one fewer registration step.
- **B2. Events as sentences.** Rylee's own twenty rule sentences (`design/named-edits-sentences.md`) are the natural form: `"when": "defeats floor-5-loud-1"` instead of `{"defeats": {"what": "floor-5-loud-1"}}`. Album stickers and rules both use it; normalised to the canonical JSON. Album: 3.0 KB -> about 1.3 KB; rules 2.5 KB -> about 1.6 KB. Agents read and write it more reliably than nested objects, and so do people.
- **B3. Name groups, not instances.** The album's "met" stickers point at instance ids (`floor-5-loud-1`), so retargeting a Blueprint family can silently break them. `defeats any barrel-mimic` (by family) survives edits. Eight of Cottage's 25 stickers are this mechanical: `"album": {"meet": "each family"}` would generate them.
- **B4. Roles as words.** Cottage's Keybearers are ordinary enemies that carry a key; the engine does not know they are guardians. A `role: keybearer` tag (a word the pack chooses) lets the lock check, the balance report and the album say "the guardian of this floor" without parsing names.
- **B5. One word per idea.** The glossary admits `floor` is both the stakes setting and a dungeon floor. Accept `stakes` as the key, keep `floor` as an alias for old packs.
Honest scale: these save about 5 KB of a 58 KB pack. The value is fewer mistakes and fewer edit sites, not bytes.

## C. Smaller engine, one vocabulary
Adding the one action `complete-act` touched **five places in three files** (maplab's key list and its checker, the bake filter in cli, the JS validity check and the JS performer). Adding a pack block (`sound`) touched the validator, the bake, a template placeholder, the JS, the feature catalog, a guide and a test. Events are listed twice (maplab and the JS `EVENTS` table). The rule grammar is kept "in lockstep" by comments.
- **Shape:** one declarative `vocabulary` file (events with their payload keys, actions with their argument shape, pack blocks with their bake variable). The Python validator and the bake read it; the JS table is generated from it and checked in, with a drift check like Blueprint's. Adding an action or block becomes one entry plus its behaviour.
- **Scale:** roughly 100 lines of parallel action/event code collapse; the real gain is that lockstep drift stops being possible. Pairs naturally with the `web/packaged.html` split (`docs/plans/player-split/PLAN.md`, #261), which is the biggest single edit-surface win (6,632 lines).

## D. Smaller docs and catalog
- `docs/features.json` is one file every feature appends to; two parallel foremen collided on it. One file per feature (or a catalog generated from the vocabulary) removes the hotspot and makes the pack-side `detect` honest (finding 5).
- `docs/guides/rulesets.md` is 777 lines holding every block. One short guide per block, each also the source of its Library chapter, keeps humans and agents on the same page.

## Order (proposed)
1. A2 and A1-at-import (smallest change, biggest bytes). 2. B1 and B5 (pure defaults; no new syntax). 3. C with the `packaged.html` split. 4. B2 to B4 as one normalising layer, only after Rylee approves the sentence form (ask-first contract change). 5. D alongside C.
Everything keeps the Blueprint rules: a canonical form that is checked in and readable, a lock against drift, and an exit ramp.

---

# Pass 2: the shapes we keep re-typing (measured 2026-10-04, after the split)

The first pass looked at the pack and the player. This one looks at the shapes the *work itself* repeats, in the Blueprint spirit: a short source that expands to a canonical form, checked in, readable, with a lock and an exit ramp. Every number was counted on the repository today.

| # | Shape we repeat | Measured | Shorter, more flexible form | Words saved |
|---|---|---|---|---|
| 1 | **Test harness boot** | 38 `*_harness.mjs` (6,253 lines); 22 build their own JSDOM, 13 define their own canvas stub; 637 lines (12%) appear verbatim in five or more. Four harnesses written last night each copied about 35 lines. | One `tests/fixtures/play.mjs` driven by a data spec: `{"steps": ["begin", "dir:right", "key:e", "wait:200"], "read": ["VEFR_ALBUM", "#combat-live"]}` prints the reads as JSON. A new feature test is a Python assert plus a 3-line spec. | about 600 lines now, about 30 per future test |
| 2 | **Fixture packs** | 15 `make_*_pack.py` (1,354 lines); every new test also re-implements "load pack, edit world.json, write it back" (about 12 lines, 12 times last night). | `pack(base, patch)` where the patch is a JSON merge: `pack("lock", {"world.json": {"sound": {"theme": "soft"}}})`. | about 150 lines now, 12 per test |
| 3 | **Shape checks in the validators** | `maplab.py` has 23 `*_errors` functions (2,721 lines) hand-writing "must be one of ...", "needs 1 to 60 characters", "names an id the pack does not declare". | One schema table (type, enum, range, required, reference-to-known-ids) rendered into the same plain sentences. The same table then gives: `vefr features --pack` detection (finding 5), generated reference docs, an exportable JSON Schema an agent can validate against while writing, and `vefr explain block album`. | an estimated third of `maplab.py`, plus the hand-typed shape tables in `rulesets.md` (777 lines) |
| 4 | **Region files repeat the look** | In Cottage, 30% of the contract fields (legend, watch, water, colours) are identical across regions (945 of 3,154 bytes); changing the deep floor look meant editing four contracts by hand. | An act-level `defaults` block with per-region overrides, like a CSS cascade; `"legend": "dungeon"` names a reusable legend. | one edit instead of four; contracts shrink by about a third |
| 5 | **Rule and sticker syntax** | (pass 1, finding B2/B3) nested objects for what people say as a sentence; instance ids where a family is meant. | `"when": "defeats any barrel-mimic"`, normalised to canonical JSON. | about 40% of rules and album text |
| 6 | **Foreman briefs** | Five briefs written last night (V2, A1, S1, W1, I1) share about 80% of their words (constraints, "foreground only", "git add only", report shape) and two earlier ones omitted a fact the later ones needed ("edit parts, not packaged.html"). | A standing foreman contract file that briefs inherit; each brief is only objective, seams, acceptance. A `brief new` command fills it. | about 60% of every brief, and fewer omissions |
| 7 | **Agent instructions** | 38 KB of `AGENTS.md`, policy and contributing text across the layers an agent loads at session start. | Not measured as redundant yet; the constitution already says never restate. Worth a one-hour read for duplicated sentences, and a check that fails when a rule appears in two files. | unknown |

## What the shapes have in common
Each one is a **sentence-sized source with a canonical expansion**: people and agents read and write the short form; the checked-in canonical form is what machines read; a lock catches drift; deleting the short form is the exit ramp. VEFR already has the proof (Blueprint: 508 values became 277, every record equal).

## Proposed order (smallest risk first, tests first, foreman-built)
1. Shared `play.mjs` and `pack()` (items 1 and 2): no contract change, pure test code, immediate savings, and they make every later slice cheaper.
2. Foreman contract file (item 6): estate tooling, no VEFR contract.
3. Schema table for the pack blocks that were added last (album, sound, walk sheets) as the first rows, then migrate validators one at a time (item 3), proving each with the existing tests (their sentences must not change).
4. Region defaults (item 4) and the sentence forms (item 5): pack-contract changes, so they wait for Rylee's yes.

---

# Pass 3: one record per thing, one ledger for art (refined 2026-10-04)

Rylee asked to refine the idea against all the game systems, including how art is generated and placed, and to find every other place the same shapes are re-typed. Counted on the repo today.

## A. The edit-site count: how many places must change for one thing
| To add... | Places touched today | What they are |
|---|---|---|
| a monster | 8 | the picture; `player.sprites`; `player.sprite_scale`; a Blueprint family; the instance(s) on a floor; an album sticker; a credits line; the hand-written credits summary |
| a piece of gear | 6 | the picture; `player.sprites`; `items` (name, sprite, slot, mods, value); who drops it (an enemy property); the credits; the shop (derived) |
| a door | 6 | a glyph in `map.md`; a legend entry for it; a transition record; a poi label; poi text; a tile picture |
| a region | 8 | the act's region list; `map.md`; `contract.json`; two transitions; a Blueprint region; a `tiles/` folder; poi text |
Five coordinate dialects describe "where": `[x, y]` arrays, `"x,y"` string keys in `pois`, `at: [x, y]` text in book front matter, glyphs in the map, and transition `at`. Last night's sealed door needed six edits in four files, and the guardians' places were computed twice by my own one-off scripts.

## B. The refined idea: extend Blueprint into the pack's source of things
Blueprint already proves the pattern for creatures (a short source, expanded to canonical files, locked, with an exit ramp). Extend that one source with the other things a game places, so a thing is **one record** and everything else is derived:
- **things**: `{"id": "copper-ladle", "slot": "hand", "atk": 2, "from": "floor-5-loud-1", "art": "copper-ladle"}`. Derived: the `items` entry, the sprite registration (by name), the drop on the carrier, the shop price, a "found it" sticker.
- **places** (per region): `{"door": "sealed", "at": [11, 1], "to": "king-room", "needs": "crown-seal", "text": "..."}`. Derived: the map glyph, legend entry, transition, poi and poi text. Chests and signs the same way.
- **placement as a sentence**: `"at": "farthest room off the path to the stair"` resolved once by `vefr normalize` (seeded, then locked) instead of a hand-computed coordinate, so a regenerated floor keeps its guardian and its sealed door. This is also the overlay lane of finding 9.
- **stickers** default from the cast (`meet each family`, `find each thing`), so nothing needs a hand-typed id.
Edit sites become: a monster 2 (art + family), gear 2 (art + record), a door 1, a region 3 (map, contract, record). The canonical files stay checked in and readable; `vefr check` rejects stale output; deleting the source is the exit ramp.

## C. Art: one ledger, not 43 hand-typed commands
Measured: 287 credits files (289 KB), 62 repeating the same style paragraph verbatim and the rest repeating the prompt once per picture in a batch; 43 `codex_batch.sh` invocations written into briefs and docs; 10 pack-side art tools (1,614 lines); 12 briefs, 4 hand-written PICKS files. Every picture followed the same path by hand: prompt, batch, contact sheet, pick, cut, size, register, credit.
- **`art/ledger.json`** (or one file per round): `{"id": "copper-ladle", "role": "item-icon", "subject": "a battered copper soup ladle...", "variants": 2, "ref": "keys-a-v1", "pick": "v2"}`.
- **Roles carry the rules**: `item-icon` = cut out, 128 px, `--clear-holes`; `creature` = cut, 128 or 256; `tile` = flatten, 96 px, grid `1x1`/`3x3`; `sheet` = 5x4 frames + the sheet JSON; `ui-part` = nine-slice. The wrong tile form (flat grey walls) becomes impossible because the role decides.
- **The style paragraph lives once** (`art/STYLE.md` gains a machine-readable block); a prompt is style + subject + the role's reference. The ledger is the prompt record, so each credits file is a three-field line (tool, date, source file) with **no absolute or temp paths**.
- **Verbs** (finding 6 grows): `vefr art make ID` (batch), `vefr art sheet ROUND` (contact sheet), `vefr art pick ID v2`, `vefr art cut ID` (cut, size, write into the pack, register by name, credit). Registration by convention removes `player.sprites` and `sprite_scale` as hand lists (36 of 38 entries were just the file name).
- Saves roughly 80% of the credits text, every registration edit, and the "which command was it" memory.

## D. Code shapes (counted)
| Shape | Count | Tight form |
|---|---|---|
| Browser storage, each access wrapped by hand | 63 `localStorage` sites, 54 get/set calls, 15 hand-built key names | one `store(name)` helper (namespacing + the try/catch once). The rule "every access is wrapped" is prose today; a lint test that bans raw `localStorage` outside the helper makes it a check, per the constitution. About -250 lines. |
| Page globals the harnesses read | 51 `window.VEFR_*` | one documented `VEFR_STATE` facade (finding 7); the bot and every harness read one object. |
| Weave placeholders | 36 in the template, 32 `replace('{{` lines in `cli.py` | a table of blocks (name, placeholder, builder); with the schema table of pass 2 the table is generated. |
| `document.getElementById` | 175 | a one-line `$()` alias; small but it shortens every new part. |
| Test harness boot, fixture packs | (pass 2) | `play.mjs`, `pack(base, patch)`. |

## E. Order (smallest and safest first; each tests-first and foreman-built)
1. `play.mjs`, `pack()` and the `store()` helper with its ban-lint: pure code tightening, no contract change.
2. The foreman contract file; the art ledger as a document and a `vefr art cut` that reads it (no pack contract change, because it only writes files the pack already understands).
3. The schema table and the block table (pass 2, item 3).
4. **Things and places in Blueprint** (B above): a pack-contract extension and an ADR, so it waits for Rylee's yes; it is the biggest tightening and the one that retires the most hand lists.
