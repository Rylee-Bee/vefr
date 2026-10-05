# Tighten the shapes: the plan (2026-10-04)

Rylee's ask: "I want our code to be as tight as possible." She picked four ideas: (1) a shared test kit and a storage helper, (2) an art ledger and `vefr art cut`, (3) a schema table for the validators, (4) things and places in Blueprint. Evidence: `docs/research/size-and-language-pass.md` (passes 1 to 3) and `docs/research/tighten-shapes-web-research.md`. Every count below was rechecked against the code today. A claim marked UNVERIFIED was not run.

## 1. Critical review

**Right.** The pattern is sound: a short source, a canonical committed form, a lock, and an exit ramp (Blueprint). The test kit (pass 2, items 1 and 2) is the cheapest win, and it makes later slices cheaper. Sprites by name (B0) is a pure default that removes 36 of 38 hand entries; I checked that only `hearth-cat -> cat.png` and `vendor -> trader.png` break the convention.

**Numbers that were too high (corrected):**
- **`store()` "about -250 lines".** The code has 54 get/set calls in 23 parts, and almost every one is a single line already. A realistic saving is 40 to 80 lines. The real value is the ban-lint, which turns a prose rule into a check. Keep it for that reason only.
- **Schema table "a third of `maplab.py`".** Only the flat blocks (`saves`, `sound`, the growth shapes, the album shape) and the event payloads fit a table. `skin`, tiles, sprite sheets and rule actions read files and check cross-references. Expect 150 to 250 lines (6 to 9%). The real value is a different find: **the event vocabulary is typed three times** (`_rule_event_errors`, `_album_when_errors`, and the JS `EVENTS` table in `web/player/parts/440-the-camera.js`), and it has **already drifted**. `maplab.py:694` says "the six events are ..." but `RULE_EVENTS` holds 11.
- **Placeholders.** There are 36 placeholders and 36 replace calls, not 32. The four rule replaces span two lines each, so a line grep missed them.
- **Credits.** 287 files exist, but only 265 are tracked; round18 is untracked work by another session. **41 tracked credits files (rounds 11 to 13) embed `/tmp/...` reference paths**, and some of them contain this session's scratchpad path.
- **Edit sites for gear.** Gear can already name its carrier through Blueprint `properties.drops`. With B0 alone, gear takes 4 edits (picture, `items` entry, drops, credits), not 6. B1 only brings it from 4 to 3.

**Over-engineered or not worth it (cut):**
- A placeholder "block table" in `cli.weave_html`. It saves about 40 lines, and `str.replace` runs in order: a pack string containing `{{...}}` is substituted differently if the order moves. Cut.
- A `$()` alias for 176 `getElementById` calls. It is cosmetic and would touch every part, which makes it a collision magnet. Cut.
- `vefr art make` in VEFR. Generation needs a logged-in Codex CLI and private prompts. It stays in Cottage as a thin wrapper over `codex_batch.sh`. Cut from VEFR.
- B3 placement sentences. This is the riskiest slice (a seeded search, then locked) and it serves floors that are not being regenerated yet. Defer it. It is a cut-line, not a slice in this mission.
- JSON Schema export and `vefr explain`. Cut-line after S2. They are cheap once the table exists, but nothing needs them now.
- A `VEFR_STATE` facade. Adopt it later. It touches many parts, so it waits until the interface stream settles.

**Missing (found by reading):**
1. `440-the-camera.js` holds three things: the camera (lines 1 to about 70), the whole rules engine with `EVENTS` (about 70 to 460), and the asset loaders. Interface slice I1 edits the camera. Any vocabulary work edits the same file. A byte-identical split (K3) removes that collision.
2. B0 leaves two gaps, and the frozen tests do not cover either one:
   - `_sprite_scale_errors` (`maplab.py:1907`) rejects any scale whose key is not in `player.sprites`. Cottage has 18 scaled sprites, so dropping the list fails validation.
   - `_player_sprite_sheets` (`cli.py:1260`) only looks at `player.sprites` entries, so `hero.sheet.json` stops baking when `hero` is named only by its file.
   - `test_an_explicit_pack_is_byte_identical_before_and_after` compares `weave_html(pack)` with itself, which proves determinism, not "before and after".
3. Three credit formats: per-picture `*.credits.txt`, hand-written `sprites/CREDITS-release1.md`, and `round16/.../CREDITS.txt`. VEFR has a fourth, `web/art/MANIFEST.json` (`{source, credit}`).
4. Cottage CI validates against a **pinned** `VEFR_REF`. Every Cottage migration must bump the pin after the VEFR merge.
5. Mission tooling:
   - In `~/missions/tighten-shapes/mission.json`, K2 has `deps: []` even though its title says it waits. `mission next` already says "dispatch K2".
   - Every task has `accept: null`.
   - K1, five web workers and UI3 were seven concurrent Bazzite jobs, against launch.md's "at most 3".
   - DECISIONS 2026-10-03 #3 says **one foreman per campaign, slices in sequence**. So this mission gets one foreman lane, and the interface mission gets the other.
6. `docs/plans/interface/PLAN.md` slice 4 names `440-the-skin.js`; the file is `540-the-skin.js`.
7. Briefs repeat about 80% of their text, and `~/.agents/skills/offload/foreman-plan-template.md` already exists. Briefs should cite it, not grow a new contract file.
8. The VEFR checkout at `~/code/Rylee-Bee/vefr` is in use right now: it is on `feat/in-world-interface` with uncommitted edits to 020, 030 and 440. This plan file is untracked there. Every slice below runs in its own worktree under `~/worktrees/`.

**What the web-research digest changes in this plan.**

Adopted:
- stable error codes with golden prose (§4);
- per-record hashed seeds (§6, B3);
- the role-to-rule table, generated credits, a per-asset `sha256`, and encoding once at import (§5);
- one frozen state facade, later, and the storage lint (K2).

JSON Merge Patch for `pack()` is already the K1 contract (`null` deletes). K1's tests do not pin the rule that a merge patch replaces arrays whole, so add one assert to K2's tests.

Where the code disagrees with the digest:
- "63 raw sites": 63 is the count of mentions, comments included. There are 54 calls.
- "stable codes": `validate()` returns `list[str]` to every caller, so the codes stay internal to the table and are pinned by `tests/test_shapes.py`. The public API does not change.

## 2. Slices

Columns: id, repo, files touched, frozen tests, acceptance, who builds it, time box. **Rylee?** marks a pack-contract change. Things and places is approved, so Rylee? is only needed where a design changes.

| # | Repo | Files touched | Frozen tests | Acceptance | Who | Box | Rylee? |
|---|---|---|---|---|---|---|---|
| **K1** test kit (running) | vefr | `tests/fixtures/play.mjs`, `tests/play_kit.py`, 5 migrated tests | `tests/test_play_kit.py` | the K1 brief command | foreman | 70 min | no |
| **B0** sprites by name | vefr | `src/vefr/cli.py` (`_player_sprites`, `_player_sprite_sheets`), `src/vefr/maplab.py` (`_sprite_scale_errors`) | `tests/test_sprites_by_name.py` plus a new coordinator file `tests/test_sprites_by_name_gaps.py`: a by-name scale validates; a by-name `hero` keeps its sheet; `weave_digest.py` lines for `sample-world`/`lore` equal a recorded constant | `bash tests/run.sh tests/test_sprites_by_name.py tests/test_sprites_by_name_gaps.py tests/test_walk_sheets.py` then the full suite | foreman | 60 min | no |
| **B0c** Cottage uses B0 | cottage | `VEFR_REF` in `.github/workflows/validate-pack.yml`, `worlds/.../world.json` (`player.sprites` keeps 2 entries) | none new | parsed `VEFR_SPRITES` and `VEFR_SPRITE_SHEETS` equal before and after; bot desktop and phone pass | coordinator | 30 min | no |
| **S0** validator golden | vefr | `tests/golden/validator/cases.json`, `scripts/golden_validator.py`, `tests/test_validator_golden.py` | itself, captured on `main` before S1 | `bash tests/run.sh tests/test_validator_golden.py` | coordinator | 60 min | no |
| **K2** `store()` and its lint | vefr | new `web/player/parts/065-store.js`, `web/player/manifest.json`, the 23 parts with storage calls, `web/packaged.html` (rebuilt) | `tests/test_store_lint.py` (no `localStorage` outside 065 and 230's parameter); `tests/test_store_keys.py` (a play-kit route; the `store` dump equals a golden captured on `main`) | both tests, `test_player_build.py`, full suite, Cottage bot | foreman | 90 min | no |
| **S1** table core: saves and sound | vefr | new `src/vefr/shapes.py`, `maplab.py` (`saves_errors`, `sound_errors`) | `tests/test_shapes.py` plus S0 golden | both, plus `test_sound.py`, `test_rules_saves*.py` | foreman | 90 min | no |
| **S2** one event table | vefr | `shapes.py`, `maplab.py` (rule and album `when` checks) | S0 golden, regenerated once for the corrected "eleven events" line, with the reason in the PR | golden, `test_rules_validator.py`, `test_album.py` | foreman | 60 min | no |
| **K3** split the camera part | vefr | `440-the-camera.js` becomes 440 (camera), `445-rules-engine.js`, `448-asset-loaders.js`; manifest | `test_player_build.py` | `sha256sum web/packaged.html` unchanged; `weave_digest.py` unchanged | coordinator | 20 min | no |
| **S3** generate the JS `EVENTS` | vefr | `445-rules-engine.js` (generated block), `scripts/build_player.py` or `shapes.py --emit-js` | `tests/test_vocabulary_drift.py` (the generated text equals the part) | digests unchanged | foreman | 60 min | no |
| **A0** clean credits | cottage | 41 `art/source/round1[1-3]/**.credits.txt`, `art/tools/codex_batch.sh` | `art/tests/test_credits_clean.py` | `uv run pytest art/tests` | coordinator | 40 min | no |
| **A1** ledger and `art cut` | vefr | ADR `docs/adr/0011-art-ledger.md`, `src/vefr/art_ledger.py`, `vefr art check` in `cli.py`, `tools/art/cut.py` (ported from Cottage `process_*`) | `tests/test_art_ledger.py` (stdlib); `tests/test_art_cut.py` (skipped without Pillow) | both | foreman | 120 min | no |
| **A2** Cottage adopts the ledger | cottage | `art/ledger/round-12.json`, `round-15.json`, `art/styles.json`, generated `worlds/.../sprites/CREDITS.md` (replaces `CREDITS-release1.md`) | `art/tests/test_ledger.py` | `vefr art check --ledger art/ledger` (hashes match the committed sprites); digest unchanged | coordinator | 60 min | no |
| **A3** Skin kit manifest | vefr + cottage | `art/skin-kit.json` (each piece: name, size, slice, role, how it is made: `draw`, `derive:<recipe>` or `copy`); `build_skin.py` reads it | `art/tests/test_skin_kit.py` | `vefr art check` prints "N of M pieces drawn, K chosen, D derived" and fails a build with a missing piece | foreman | 90 min | no |
| **A4** `vefr art draw` | vefr | one piece per call from the kit; style file (palette, references, the shared style block) read from data; private output folder per job; writes the ledger entry as `draft` | `tests/test_art_draw.py` (dry-run prints the exact prompt; a multi-piece brief is refused) | dry-run only in CI; one real draw by hand | foreman | 90 min | no |
| **A5** `vefr art picker` | vefr | builds a picker page from the kit and the drawn variants, and writes the picks back to `art/ledger` as `approved`/`redraw` | `tests/test_art_picker.py` (page builds, picks round-trip through a fixture store) | the page opens with every piece shown beside the chosen ones | foreman | 90 min | no |
| **B2** places | vefr | `src/vefr/blueprint.py` (format 3), `maplab.py` touch-points, fixtures `tests/fixtures/blueprint/v3/` | `tests/test_blueprint_places.py` (written from §6) | the test, plus `test_blueprint*.py` and Cottage trial | foreman | 150 min | **yes** (§8 Q1) |
| **B1** things | vefr | `blueprint.py` (format 2), fixtures `v2/` | `tests/test_blueprint_things.py` | the test, plus the trial | foreman | 90 min | no |
| **B4** stickers from the cast | vefr | `blueprint.py` or album expansion | `tests/test_album_from_cast.py` | the test, plus the album tests | foreman | 60 min | no |

Format numbering: B2 lands before B1, but the files number them the other way round: places is format 3, and format 2 is reserved for things. A format-3 file is complete on its own; it never waits for format 2.

## 3. Collisions and sequencing

**Lanes.**
- Foreman lane T (this mission, one at a time): K1, then B0, K2, S1, S2, A1, B2, B1, B4.
- Foreman lane I (the interface mission, UI3): I1, then slices 2 to 6.
- The coordinator works on the VM, in a worktree: S0, the B0 gap tests, B0c, K3, S3 dispatch, A0, A2, ADR amendments.

**Files both lanes touch.**
- `web/packaged.html` is generated. A conflict there is never merged by hand: rebase, then run `scripts/build_player.py`.
- `web/player/manifest.json` changes when K2 or K3 adds a part and when interface slices add parts. The PR that lands second rebases.
- I1 edits 020, 030 and 440. K2's 23 parts do not include any of them, so **K2 does not have to wait for I1**. It needs K1, because its key test uses the kit. Fix the mission: K2 depends on K1. Interface slices 4 and 5 may touch `200-pause-menu.js` and `100-speech-box.js`. K2 changes one line in 200, which is a trivial rebase.
- K3 must wait for **I1 to merge**, because both edit 440. S3 waits for K3.
- A0 and A2 edit Cottage `art/`. Another session is on Cottage branch `art/soft-wood-skin` with an untracked `round18/`. Run them in a Cottage worktree from `origin/main`, and touch only rounds 11 to 15, `art/tools/codex_batch.sh`, `art/ledger/` and `sprites/CREDITS*`.
- B0c, A2 and the B2/B1 trials all edit Cottage `worlds/`. Run them one after another.

**Critical path.** K1 (running), then B0, then B0c and the ADR 0010 amendment, then B2, then B1, then B4. The schema track (S0 to S3) and the art track (A0 to A2) fill the foreman gaps. Order of the lane-T queue after K1: B0, K2, S1, S2, A1, B2, B1, B4. The coordinator does S0 and the B0 gap tests now, A0 after the Cottage skin branch merges, and K3 after I1 merges.

## 4. The schema table

The table lives in `src/vefr/shapes.py` (stdlib only):

```python
@dataclass(frozen=True)
class Key:
    name: str
    kind: str                 # 'str' | 'int' | 'bool' | 'enum' | 'obj' | 'list' | 'ref'
    choices: tuple = ()       # enum values, in sentence order
    lo: int | None = None     # int range or str length
    hi: int | None = None
    ref: str | None = None    # 'item' | 'place' | 'thing' | 'enemy' | 'book' | 'phase' (from _rule_known_ids)
    required: bool = False

@dataclass(frozen=True)
class Block:
    name: str                 # 'saves'
    example: str              # '{"rules": "persist"}'
    keys: tuple[Key, ...]
    say: Mapping[str, str] = {}   # error code -> sentence template override (golden prose)

Problem = namedtuple('Problem', 'code pointer sentence')
def check(block, value, known=None) -> list[Problem]

EVENTS = {
    'starts': (),
    'enters': (('place', 'place'),),
    'comes-near': (('who', 'thing'), ('distance', Key('distance', 'int', lo=0, hi=9))),
    ...                       # 11 rows, same order as RULE_EVENTS
}
```

**Error codes** are stable: `not-object`, `unknown-key`, `missing-key`, `not-in-choices`, `out-of-range`, `wrong-type`, `unknown-ref`. Tests pin the code and the pointer; the golden file pins the prose.

**How a sentence is made.** Each code has a default template, for example `not-in-choices`: `'{path} must be {choices}'`, where choices render as `"persist" or "reset"`. A block's `say` overrides the default per code. For example, `sound` needs three overrides to stay byte-identical (`"sound may only hold theme, not '{key}'"` and two more); `saves` needs none except `unknown-key`.

**Emission order matches today:** stop at `not-object`; then unknown keys in the value's own order; then each table key in table order (missing, then value). `validate()` keeps returning `list[str]`, so no caller changes.

**Proof that sentences stay the same.** The existing tests mostly match substrings (`test_sound.py` asserts `any("sound" in e ...)`), so they **do not** prove byte identity. S0 adds a golden file: about 60 mutation cases built with `pack(base, patch)` merge patches, covering every sentence branch of the functions that will migrate. The expected `validate()` lists, order included, are captured on `main` before S1. One sentence changes on purpose: "the six events" becomes "the eleven events" in S2, regenerated with the reason written in the PR.

**Migration order.** S1 `saves` and `sound`, then S2 the event table (rules and album), then S3 the JS twin. Growth and the album shape follow only if S1 and S2 show at least 60 lines saved. `skin`, tiles, sheets and rule actions stay hand-written.

## 5. The art ledger

**File.** `art/ledger/round-NN.json` in Cottage, one file per round. One file per round avoids the hot spot that `features.json` became.

```json
{"ledger": 1, "round": 19, "made_with": "codex", "style": "storybook-item", "date": "2026-10-05",
 "pictures": [
  {"id": "copper-ladle", "role": "item-icon", "subject": "a battered copper soup ladle with a long wooden handle",
   "variants": 2, "ref": "art/source/round13/keys_a/keys_a_v1.png",
   "pick": 2, "to": "sprites/copper-ladle.png", "sha256": "...", "status": "draft"}]}
```

Key sets are closed:
- top level: `ledger`, `round`, `made_with`, `style`, `date`, `pictures`
- picture: `id`, `role`, `subject`, `variants`, `ref`, `pick`, `to`, `size`, `grid`, `sha256`, `status`, `note`

`style` names an entry in `art/styles.json` (the paragraph, stored once). `STYLE.md` stays the human record. A prompt is the subject, then the style paragraph, then the role's sentence.

**Roles** (`ROLES` in `src/vefr/art_ledger.py`; neutral engine facts):

| Role | What `cut` does |
|---|---|
| `item-icon` | cut from the corners, `clear-holes`, fit 128, bottom-aligned |
| `creature` | the same, without `clear-holes`; `size` may be 256 |
| `tile` | flatten opaque, centre-crop, `grid` 1x1 or 3x3, 96 px per cell |
| `sheet` | grid cut, 128 px frames, writes `<id>.sheet.json` (Cottage hero: 5x4, idle plus 4 walk frames per direction) |
| `ui-part` | `box` or `strip` with `size` and `slice` (absorbs `build_skin.py`'s geometry rows) |

**What lives where.**
- **VEFR:** the ledger schema, the role table and `vefr art check` (stdlib). `check` validates the keys, recomputes `sha256` of every `to` file, renders the pack credits and enforces the **clean-credits rule**: no absolute path, `~`, `/tmp`, `/home`, `..` or path outside the repo in any ledger or credits text. VEFR also gets `tools/art/cut.py`, run with `uv run --with pillow`, because Pillow is not a VEFR dependency. It is ported from Cottage's `process_sprites.py`, `process_tiles.py` and `process_ui.py`, with their tests.
- **Cottage:** the ledgers, `styles.json`, `STYLE.md`, briefs, PICKS, `build_skin.py`'s look-specific table, and `codex_batch.sh`. `codex_batch.sh` changes in A0: it rewrites references relative to the repo and copies outside references into `OUT/refs/`. A Cottage `art/tools/ledger_make.py` (optional, later) turns a ledger into `codex_batch.sh` calls.
- **Credits.** New rounds write no `*.credits.txt`, because the ledger is the record. Old ones stay as history once A0 cleans them. `sprites/CREDITS.md` is generated in the `{source, credit}` shape of `web/art/MANIFEST.json`.
- **Encoding.** Pictures are encoded once, at cut time. The suffix of `to` picks the format, and WebP is lossless by default. The weave never re-encodes.

## 6. Things and places

**Order.** I changed it to B0, then B2, then B1, then B4, with B3 deferred. Places give the biggest saving: a door goes from 6 edits in 4 files to 1. Things give the smallest (gear from 4 to 3).

**B2 places (the next format).**
- `REGION_KEYS` gains `places`.
- PLACE_KEYS is closed: `id`, `kind` (`door` | `stair` | `sign`), `at`, `glyph`, `tile`, `base`, `label`, `text`, `to`, `to_at`, `needs`, `locked_text`.
- `chest` is left out until the engine has a chest place to point at (UNVERIFIED).
- Required: `id`, `kind`, `at`, `glyph`. `to` and `to_at` come together and are required for door and stair. `needs` and `locked_text` are door-only and need `to`.
- Expansion writes:
  - `contract.json /legend/<glyph>` = `{base, solid?: no, tile}`, where `base` defaults to the region's `"."` base;
  - `/pois/<x,y>` = `label`, and `/poi_text/<x,y>` = `text`;
  - one act `transitions` entry `{from, at, to, to_at, requires: {item: needs}, locked_text}`, appended after the hand-written ones so the hand transitions keep their `transition {i}` numbers;
  - the map cell.
- **The glyph is written into `map.md`**, not overlaid. `_door_tile_problem` validates doors against `map.md` plus the legend, the bot and the studio read `map.md`, and an overlay breaks the exit ramp, because deleting the source would delete the doors.
- **Stale rule** (extends ADR 0008): output is stale if the lock hash differs, or any owned pointer is not structurally equal, or the owned cell's character differs from `glyph`.
- **Errors**, each a sentence with a pointer: a glyph already in the hand legend with a different value; a hand transition with the same `from` and `at`; `at` outside the map; `needs` naming an undeclared item; a duplicate place id.
- **Exit ramp:** delete `places`. Every written value is already the old shape.

**B1 things (the format after).**
- `TOP_KEYS` gains `things`.
- THING_KEYS is closed: `id`, `from`, and the item fields `_player_items` reads today (`name`, `sprite`, `value`, `heal`, `use`, `keep`, `slot`, `mods`, `light`; the B1 test freezes the list by reading `cli.py` first).
- Expansion writes `world.json /items/<id>`, and `sprite` defaults to `id`. The Cottage trial needs the 7 items whose sprite is not their id to keep their explicit `sprite`.
- `from` adds the id **at the end** of the carrier's expanded `drops`. This is the one named exception to "lists never merge". It is an error if the carrier's drops already list the id, or if the carrier is not in a region the Blueprint owns.
- A hand `items` entry with the same id is an error.

**Traps.**
- mixed ownership: `contract.json`, the act `world.json` and `world.json` hold hand values and owned values side by side. The lock records owned pointers. On the first write, owned keys are appended at the end of hand-written dicts; later writes update them where they are. Normalize never touches a pointer it does not own;
- every new key is a format bump, with its own reader and fixtures, and v1 packs stay byte-for-byte unchanged;
- region pointers use the `~1` escape;
- bump Cottage's `VEFR_REF` before any trial.

**B3 (deferred).** If it is built, each placement's seed is `sha256(pack seed, record id)`, never one shared random stream, and it asks the lock graph in `locks.py` for "the farthest room off the path".

## 7. Proof and rollback

- **Same digest** (`scripts/weave_digest.py`, run locally, because CI cannot see Cottage): K3, S1, S2, S3, A2, and B0 for explicit packs.
- **Parsed equality plus the bot**, because a reordered dict changes the bytes but not the behaviour: B0c, B2 and B1 trials. Every owned record must be structurally equal to the hand version before the migration, and the Cottage playthrough must pass on desktop and phone, plus `axe_panels.py`.
- **Store golden plus the full suite plus the bot:** K2.
- **Validator golden:** S1 and S2.
- **Rollback.** Each slice is one squash-merged PR, so rollback is `git revert <squash sha>`. Cottage slices also revert the `VEFR_REF` bump. Blueprint slices also have the exit ramp: delete the source and the lock.

## 8. Risks, cut-lines, questions

**Risks.**
- Collisions on `packaged.html`: rebuild, never merge by hand.
- The foreman lane runs one job at a time and the VM is small. Keep Bazzite at 2 foremen plus at most 1 research worker.
- B2 is the biggest diff; time-box it, and if it overruns, ship doors only and leave signs for later.

**Cut-lines, if time runs short, in this order:** B4, then S3, then A2's back-fill (cut only new rounds), then B1.

**Questions only Rylee can answer (each blocks one slice):**
1. **B2: write door glyphs into `map.md` (recommended) or overlay them at weave time?** Writing keeps the map honest and keeps the exit ramp. ADR 0010 currently says overlay.
2. **Places before things (recommended), or things first as ADR 0010 lists them?**
3. **B3 placement sentences: defer (recommended) or build in this mission?**
