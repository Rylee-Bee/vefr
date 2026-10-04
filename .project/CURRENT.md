# CURRENT — vefr

> **Live truth lives in `git log`, `gh pr list`, and the gate.** This
> file is orientation, not a mirror of HEAD. Refresh it when the
> *phase* changes; let Git tell you the SHA.
>
> Last refreshed: 2026-10-04, late afternoon (the endless-dungeon ADRs, B2 places, the agent-platform move).

## 2026-10-04, late afternoon (slices landing; three ADRs decided)

**Landed on main since the evening note:** #275 the stage and phone dock, #276 one `store()` helper (K2), #277 sprites by name (B0), #278 E0a bench, #281 schema table core (S1), #283 art ledger (A1), #286 source art from the Media Archive, #287 fog as a bitset (F1), #288 sleeping monsters (E0d), #289 the v3 floor generator (E2), #290 skin kit manifest (A3), #291 four audit fixes, #292 places in Blueprint format 3 (B2), #293 ADRs 0013 to 0015 (Proposed).

**Decided by Rylee (recorded in the ADRs and in DECISIONS):** the wake rule, noise ranges, the warden's behaviour, reload, affix style, six starting stamps and their rotation and rarity rules, the shortcut item and the final boss's region. See `.project/DECISIONS.md` (2026-10-04, late afternoon).

**Running:** E7 elites and groups (foreman), B1 things (foreman). **Next, in Rylee's order:** E5 stamps, then E8 wardens and vaults.

**Known:** the 128x96 monster-turn bench was not rerun after E0d (the bench needs reworking for sleeping monsters); #269, #259, #260 still open. The orchestration tooling now lives in `Rylee-Bee/agent-platform` (the `agents` repo is archived).

## 2026-10-04, evening (the endless dungeon is designed and measured)

**Decided by Rylee:** the dungeon becomes sections of 8 to 11 generated floors, each ending in a key warden and a vault; acts change the town only; the King ends Act 3; an endless mode follows. Everything is a VEFR feature so any game can remake it; Cottage supplies data. Design `docs/plans/endless-dungeon/DESIGN.md`; Opus build plan `docs/plans/endless-dungeon/PLAN.md` (slices E0 to E10); epic #273. Cottage's matching rework is Cottage #91.

**Measured (E0a, #278):** generation under 1 ms at 48x32 to 128x96 in Python and JS; the monster turn (10.8 ms at 64x48, 33 ms at 128x96, budget 8) and fog saves (10 to 78 KB per floor) are the limits. **Decided:** monsters sleep until near and the flood fill is bounded to a radius (E0d); fog becomes a bitset (F1) after K2; sizes are picked per section. **Read (E0b):** a lock can test a flag; generated regions can likely be inserted into the player's region tables; fog is stored as "x,y" strings.

**Open PRs:** #275 interface (draft, held for UI3c), #276 K2 storage helper, #277 B0 sprites by name, #278 E0a bench and report. Merged today: #264, #266, #271, #272, #274.

## 2026-10-04, later (the player is built from parts; two plans are running)

**Landed on main:** the player split (#264: `web/packaged.html` is generated from `web/player/parts/`, never edited by hand; `scripts/build_player.py`, `scripts/weave_digest.py`, `tests/test_player_build.py`), the size-and-language research (#263, #265) and the tighten-shapes plan (#266).

**In progress, tracked by epics:** the in-world interface ([#268](https://github.com/Rylee-Bee/vefr/issues/268), `docs/plans/interface/PLAN.md`; slice I1 built on `feat/in-world-interface`, held until the phone dock I2 passes) and tighten-the-shapes ([#267](https://github.com/Rylee-Bee/vefr/issues/267), `docs/plans/tighten-shapes/PLAN.md`, ADR 0010). Rylee's decisions on 2026-10-04: parchment and soft wood with Ledger type (Crimson Pro); doors and stairs write their glyphs into `map.md`; places before things; placement sentences are in scope with a six-word language; sound stays on by default.

**How agents work here now:** edit a part and run the build; tests first and frozen; one foreman per lane; merge main into a branch yourself; the Cottage bot (`cottage-of-the-breeze/tests/playthrough/`) is the player-level proof.

**Known and filed:** the rule-event list is typed three times and has drifted (#269); region names show raw in hints (#259); `vefr look` cannot start in a region (#260).

## 2026-10-04 (Cottage Release 1: what landed, what it taught, where things stand)

**Release 1 is a complete, polished Act 1 of Cottage of the Breeze, built through VEFR.** Acts 2 and 3 remain part of the larger three-act direction; stopping after Act 1 was Rylee's decision, not a limit of the engine. Act advance and status effects are the next capabilities *because* the future acts will want them.

**Landed on main (all CI green):** `complete-act` rule action (#252, one accessible end card, once per save; it does not advance acts), `vefr check` follows the locks (#253: a key that cannot be found, sits behind its own lock, or could be sold), the sticker album slice 1 (#254), the up-stairs label fix (#255), **sound** (#257: a pack opts in with `sound: {"theme": "soft"}`, nine synthesized cues, one switch in Menu > Display, on by default), **walk sheets** (#258: an optional `<key>-sheet.png` + `<key>.sheet.json` gives a character a walk cycle), and the plan to split `web/packaged.html` (#261, `docs/plans/player-split/PLAN.md`, `scripts/weave_digest.py` as the byte-for-byte proof). Earlier the same day: equipment was finished (#244 to #251) and Cottage uses it.

**What the run taught:** `docs/research/cottage-release-1-learnings.md` ranks ten evidence-backed findings (seven new, three deepened) with a class and a priority each; the roadmap's NOW/NEXT/LATER board is built from it. Journal entries: `.project/DECISIONS.md` (2026-10-04).

**Open and known:** `point-to` accepts only region ids (#259); `vefr look` cannot start in a given region (#260, generalised by finding 2 of the record); the feature catalog does not detect `sound`, `walk-sheets`, `album` or `rule-saves` in a pack (finding 5); sound is on by default where a pack opts in, which sits awkwardly with the README's "nothing makes a sound unless you turn it on" (that sentence is about the studio's Boiler Room; the default for games is Rylee's to rule on); `stakes` is documented but has no player mechanic, so death is always the cozy wake-in-the-temple.

**Next, in order (see ROADMAP):** the NOW board (story draft status, scenarios, stage-containment checks, obtainability), then act advance and status effects (fire first), random floors phase 2, the native in-world interface (`cottage-of-the-breeze/docs/plans/native-ui/PLAN.md`), and the `packaged.html` split before more features land in it.

## 2026-10-03 (the packet lands; equipment step 1)

**Also landed the same day:** the **pure equipment engine** (`window.VEFR_EQUIP_ENGINE`, [PR #247](https://github.com/Rylee-Bee/vefr/issues/247)): the sums, the four named refusals, the swap, the health clamp and `clean`, all pure and pinned by a jsdom harness against the real woven file. **#218 is closed** ([PR #248](https://github.com/Rylee-Bee/vefr/issues/248)): teal text got its own token with a 4.5 floor, and the dead `--teal-light` hover is gone. **The #218 caveat is resolved:** the private pack's skin sets only `on_panel` and `on_panel_dim` and never overrides teal — the "dusk teal" in that pack is paint in the floor tiles, not a UI token — so no companion change is needed there.

**Owner decisions taken 2026-10-03 (in chat):** the language packet is **approved** (GO WITH CONSTRAINTS; the gate is released, the earned scope only — see `DECISIONS.md`); the guardian naming for #215 follows the **Diablo III Keywarden** precedent — a role label plus a proper name, not a court rank; and after A3 the order is **wave-2 staleness first, then the album**.

**Landed (main `2e8cc27`, every check green and merged):**
- **The language-architecture research packet** ([PR #242](https://github.com/Rylee-Bee/vefr/issues/242), `docs/research/language-architecture/`, 13 documents): the Phase A disposition is **GO WITH CONSTRAINTS**. The evidence earns an *optional, build-time* source layer — and the Blueprint, which is that first slice, is already built and trialled on Cottage. The evidence explicitly does **not** earn a new runtime, event sourcing, a logic engine, natural-language authoring, a plugin system, an estate-wide kernel or broad pack migration. Prior-art claims about Datalog/JSON Schema/event sourcing were corrected; some project-history claims stay `UNVERIFIED`. The Opus brief and the open decisions are `13-opus-brief.md` and `11-open-decisions.md`.
- **Equipment, the pack fields** ([PR #244](https://github.com/Rylee-Bee/vefr/issues/244), #217 track A slice A1): an item may carry `slot` (one of `hand`, `body`, `head`, `feet`, `charm`) and, only beside it, `mods` (`atk` and `hp`, whole numbers 0 to 9, bools refused). A slotted item may still carry `value` and `keep` but not `heal`, `light` or `use`; an item a locked door names as its key may not be worn. The 19 strict xfails from #239 now pass. Additive: a pack with no `slot` anywhere is unchanged, and nothing at runtime reads the fields yet.
- Smaller, same day: the localStorage fix (#224) in the player, the jsdom harness fix that took the suite from 274 s to 154 s (#241, now ~144 s), and the validator covering every act of a multi-act pack (#236).

**Decisions recorded in `.project/DECISIONS.md` (2026-10-03):** the equipment contract rules above, and that the validator and the bake read **one** function (`item_slot_and_mods`) instead of each re-implementing the five slots — the second-consumer rule from 2026-10-02 applied at the smallest scope that needs it.

**The one gate waiting on Rylee:** the language packet authorizes nothing until she has read the disposition and says go (`11-open-decisions.md` item 6). Until then the next implementation work is the ordinary backlog, not the kernel.

**Known gaps:** the stale `blueprint.cpython-312.pyc` that the 2026-10-02 plan recorded as a live hazard (same mtime to the second, same size, wrong `FIELD_ORDER`) is **gone** from this checkout — resolved, no longer a risk. The hazard's habit is still real: use `PYTHONPYCACHEPREFIX` for checks after any temporary edit.

**Equipment is now playable end to end** (A1 pack fields #244, A2 the pure engine #247, A3 the Bag panel #249). Remaining in `design/equipment.md`: step 4 (the glossary: *equip*, *take off*, *slot*; the rulesets and player guides) and step 5 (the private pack's cloak, bow and ring wired to the round-8 icons). The 1x1 fixture sprites are engine-test canon, **not** art — the real icons do not exist yet.

**Next, in order:**
1. **Equipment step 5, the pack demo** — the *only* thing left in the equipment thread. The engine is done and verified; what remains is pack data, and it lives in the private pack repo, so the engine records the companion change instead of editing across the boundary (`docs/guides/equipment-pack-companion.md`). The ring is ready to become a charm slot today and needs no new art; **a cloak and a bow do not exist in the pack yet and their names are Rylee's.**
2. **The weighted descent** (random floors phase 2, with weights) — self-contained, and it unblocks #215, whose only remaining blocker is the per-guardian proper names.
3. **The album** (#216) — write the frozen contract first.
4. **A real act 2** (#217's other half).
5. **Damage types, status effects and resistances** (`design/elemental-and-status-effects.md`) — a campaign, not a slice, and it should open with an ADR.

**Not dispatchable to a worker, and why** — so the next session does not re-litigate it. **#215** needs a new `guardians` pack block, which is a pack-contract change (ask-first), and its design says in writing that the names, the treasure and the lore note's words are Rylee's: *"nothing is canon until she writes or picks them."* The blocking step is a decision, not code. **#216** (album) and **#143/#144/#145** (Ink, audio pairing, richer floors) have no contract to test against; dispatching a worker to write both the spec and the code is how this repo ends up with a mess. Write the contract first, then dispatch.

## 2026-10-02 (the language campaign)

**Landed (main `8ce399f`, every PR green and merged):** the language-architecture campaign, built by offload foremen to tests written first, then reviewed by the integrator.
- **Blueprint** (`docs/adr/0008-blueprint-format.md`, `docs/guides/blueprint.md`): an optional `blueprint.json` expands into region `enemies` lists with `vefr normalize`; generated lists and `blueprint.lock.json` are committed and read-only; stale output is refused by `check` and the weave. **Cottage trial passed:** 508 authored creature values became 277 (45.5% fewer), 69 records equal to the hand-written ones, woven player identical. Exit ramp: delete the two files.
- **Rule saves** (`docs/adr/0009-rule-saves.md`): a pack's `saves` block (`rules` persist or reset, `legacy` fresh or from-log). Default is reset, today's behavior. Persist keeps fired rules, flags, beliefs and items under `vefr-rulestate-<world>`; `starts` fires once per save.
- **Locked doors and stairs** (`design/gates-and-guardians.md`, build step 1): `requires` (one item or one flag) and `locked_text` on a transition. Keys are never consumed.
- Research and plans: `docs/research/language-architecture/` (the Phase A packet, GO WITH CONSTRAINTS) and `docs/plans/` (the two Opus plans).

**Decisions (Rylee, in chat):** the source layer is called Blueprint; the source is the edited truth; rule saves are a per-pack setting; the first lock is Cottage's floor 3 to floor 4 stair; the key is an actual key; guardians are variants of existing monsters named from their art and abilities. Recorded in `.project/DECISIONS.md`.

**Known gaps:** none open from this campaign ([#224](https://github.com/Rylee-Bee/vefr/issues/224), the player dying on Begin when `localStorage` throws, is fixed and its test passes). The Cottage diff for the Blueprint was large in bytes only because the legacy records used several key orders.

**Next, in order:** the guardian ladder and the Cottage lock on the floor 3 stair (names are hers to approve), then the album (#216), then equipment and a real act 2 (#217).

**Late additions (2026-10-02, night):** the validator now checks every act of a multi-act pack (PR #236); equipment and a real act 2 are planned and approved (the plan is Opus's, in the session scratch; the decisions are in `.project/DECISIONS.md`): equipment as written, `complete-act` as a rule action; the next slice is the equipment tests. Image generation is `offload image` and the MiniMax MCP; Rylee prefers cute storybook mobs and Codex for characters, MiniMax for items (recipe in Cottage `art/STYLE.md`). Workflow quirks and dead ends are in `.project/DECISIONS.md`, "lessons: workflow quirks and dead ends".

**How the foremen work (tool lessons, also in `~/.agents/skills/offload/FOREMAN.md`):** commit tests first and merge them; write one brief per slice with its single acceptance command (`--runxfail`); the foreman must wait on workers in the foreground; clones need `~/worktrees/node_modules` linked for the jsdom tests; a foreman commits its `PLAN.md` by habit, so bring over only the files you mean; review every diff (each success so far needed a fix: a circular import, loose types, an unsafe copy, test-only code in the player).

## 2026-10-02, later (the foremen round)

**Landed (main `fb46af3`):** the **skin loader** (a pack's `skin` folder is validated, baked as data URIs and painted by the player; `design/ui-skin.md` steps 4-5), **random floors phase 1** (`delve.prng`, `generate_floor_v2` and the exact JS twin `window.VEFR_DELVE`, parity-tested), the **features catalog** (`docs/features.json`, `vefr features`, read-only `GET /api/features`, two shelves in the studio, a drift check in the test suite), **art in the repo** (`web/art/MANIFEST.json`, `tools/art/import_art.py`: 18 stickers, the delve set, surface tiles, 13 theme kits; every file credited), three **Library chapters** (rules, getting stronger, one button), and the Kenney sheets removed.
**Built by three offload foremen at once** (skin, floors, features) to acceptance tests written first. Each foreman stopped and escalated rather than bend a frozen test: two were real bugs in MY tests (a harness that truncated its output, a 60-vs-50 count, a mkdir without exist_ok, a wrong key). Fix the test, not the foreman. Their code needed no changes.
**Unverified:** the Containerfile now copies `docs/features.json` (so the deployed studio's shelf is not empty); no image was built.
**Done since:** Cottage uses the skin (VEFR #211 fixed the accessibility problems found by measuring it); the declutter (Interact big, Talk/Whisper/Bag/Explore small icon buttons, the Dusk/Dawn rail in Menu > Display, the top bar just Menu; it also fixed the phone HUD overlap). **Next, in order:** (1) random floors phase 2 (`descent` block, run seed, depth tables, the guardian ladder, the New descent button) and the locked stair; (2) the album; (3) cut the guardians and the cast to sprites and wire them.

## 2026-10-02 (the Cottage day)

**Landed and merged (main `2f0f40d`, gate green: ruff, public-surface, sample-world validates, 1272 passed 3 skipped):**
- **Growth** (`design/growth.md`, built): optional pack `growth` block, `levels` (classic XP and levels) or `practice` (learn by doing), enemy `xp`, the pure `VEFR_GROWTH_ENGINE`, wired into the woven player. Built by an offload foreman from acceptance tests written first (`docs/plans/growth/`).
- **Interact continues whatever has the screen:** E/F/Space/Enter turn note pages then close, and close a speech box (`tests/test_overlay_interact.py`; checklist line in `docs/guides/rulesets.md`).
- **Dev verbs:** `vefr publish`, `vefr look` (screenshot + text standing over the map), `vefr probe` (fire rule events, read the why-log), and `vefr doctor` lists tooling rows (`src/vefr/devtools.py`, `docs/plans/devtools/`).
- **First independent pack's repairs** (PR #192/#193, 2026-10-02 morning): `opens`/`reads`/`defeats`/`buys`/`sells`/`phase-changes`, `takes`, `keep`, the Why and Where-next panels.
- **Tooling:** `tests/run.sh` (throwaway clones: links node_modules, offline, pulls the `test` group); `.gitignore` matches a node_modules symlink.
- **Kenney sheets removed** from `worlds/sample-world/` (Rylee: ship only art we made, attributed; Kenney is prototyping only; LimeZu only in a project she names).

**Designed, waiting for Rylee (proposed, no code):** gates and guardians (`design/gates-and-guardians.md`: a `requires` lock on a transition, a ladder of key-carrying guardians ending in the Cellar King); the album (`design/album.md`: one record of what you have met, a sticker album first, bestiary/items/map views later); equipment (`design/equipment.md`); random floors per run (`design/random-floors.md`); act advance (ADR 0006).

**Known gaps / next, in order (all in `web/packaged.html` unless noted):**
1. Quiet-UI pass (Rylee chose "2 + 1"): the how-to-move line vanishes after the first step, the place name shows briefly, drop the use-hint that repeats the Interact button, show the fight buttons only when something is near, and tuck the rest into a small collapsible corner panel (screen readers still hear everything). Use `vefr look` to see it.
2. The hero's step hop much smaller (constants `STEP_HOP` 0.06, `STEP_LEAN` 6, `STEP_SQUASH` 0.12 near line 3214; she wants about a third).
3. Trade closes with E/F (Space/Enter keep activating the focused button); full WASD (W/A/S/D move, A/D turn note pages).
4. ~~The locked stair~~ **done**; the guardian ladder, then the album, then per-run floors.

**How to work here:** read `AGENTS.md`; run the gate in the "Commands" block; small VM (2.6 GB): never run the test suite while a Codex or heavy job runs (an exit-137 kill happened). Foremen: write the acceptance tests first, commit, `git worktree add ~/worktrees/<name>` on Bazzite, `bash tests/run.sh ...` as the `--accept`, `nice -n 10 offload foreman -m foreman ...` (the dev VM has no MiniMax key). Review every foreman diff by hand; two real workarounds and a stray `PLAN.md` showed up this way.

## Earlier

### 2026-10-01 (one long day, superseded where it conflicts with the above)

**Landed and merged:** the studio loop's first slice (put a character in the game, play it in the studio, the edit log with one-level undo, the first-playable walk; `design/close-the-loop.md`,
`docs/guides/studio-edits.md`); grid tiles (one picture drawn as cells); the `vefr` front door with `vefr find`; Lab 1; first-run fixes; hero motion; the glossary with plain names first.
**Landed, recovered from a crashed offload Foreman fleet (2026-10-01):** the **rules engine**
(optional `flags`/`claims`/`people`/`rules` pack keys, the `maplab` validator, the pure engine wired into six player events with a `window.VEFR_WHY` log, and the Desk **Undo last edit** button;
`design/rules-when-then.md`) and **one-button Interact** (one verb on `E`/`Space`/`Enter`/`F` with the label, ring and gentle nudge; combat folded in; and **Start over** in the pause menu;
`design/one-button-interact.md`). Both were built by throwaway `offload` Foreman clones whose sessions crashed; the commits were rescued, merged, gated and landed by this session.
**Designed, approved to plan (no code yet):** named edits (`design/named-edits.md`), equipment with five slots (`design/equipment.md`), and a swappable UI skin (`design/ui-skin.md`).
**Deployed:** the studio at the home host from the merged commit; checked at runtime (health, the new routes, a weave and an inline play, a preview that wrote nothing).
**Known gaps:** the rules **Why did that happen?** button / `vefr why`, the Cottage rules demo and `add_rule` edits are not built (rules Tasks 5-7); the first-playable sticker is parked until a picture is chosen; the placement preview copies the whole pack to check it.
**Next, in order:** equipment; the rules why-log button and `vefr why`; the Cottage rules demo; `add_rule`/`add_reaction` edits; the UI skin tools and loader.

## Phase

**The studio grows by building its first game (owner, 2026-09-25).**
The engine is the bones; games are the flesh, in private pack repos.
The engine now grows one ruleset at a time, each one pulled in by the
first studio project: a classic town-and-dungeon roguelike remake in a
private pack. The owner learns game-making by building it; the engine
gets fun and accessible by carrying it. The BJ pack is paused and
becomes the **launch title** later.

Landed so far (all in `ROADMAP.md`): boundary, cooking, desk, rulesets guide,
Library L1 and L2, delve, fog of war, combat, loot + bag, the reward end
(gold, shop, using a thing), regions + doors, and - this stretch - the
commission board, the woven camera and sprites, the studio handbook, books
found in play, **autoexplore**, the **fog toggle**, **author grammars**, and
the **torch/reveal light**.

**The one next step:** the open `Next` entries in `ROADMAP.md` (enhancement
waves 1-2 and the studio items). Each pack-contract change is its own
ask-first. The old "play Act 2 before Act 3+" gate is retired by owner
decision (estate vision Q9).

**The north star (owner, 2026-09-30):** anyone can make their own game, their
own way - documented and taught. It decides what gets built next.

## Where things live

The vision and plan are **outside this repo on purpose** — they carry
private canon, and this repo is public.

| What | Where |
|---|---|
| Vision (owner's words govern) | estate `docs/vefr/VEFR-VISION-INTERVIEW-2026-09-22.md` |
| Plan: phases, acts, gates | estate `docs/vefr/VEFR-GAME-PLAN-2026-09-22.md` |
| Act 1 spec | estate `docs/vefr/VEFR-ACT1-SPEC-2026-09-22.md` |
| Older direction docs (09-21) | estate `docs/vefr/` (product direction, orchestration plan, inventory) |
| Demo game pack + its characters | `code/Rylee-Bee/burrito-journalism` (private; D7) |
| Engine UI | `web/` (workshop + `packaged.html` player); mockups in `design/` |
| Landed-change ledger | `ROADMAP.md` |
| Durable decisions | `.project/DECISIONS.md` |

The estate `media_files/designs/` holds copies of some plan docs.
Treat `docs/vefr/` as the canonical copy.

## Open owner decisions

1. **The guardian names** (#215). The only thing blocking that slice.
   Rylee asked "how does Diablo do it?" on 2026-10-03; the precedent is
   D3's **Keywarden** — a Super Unique (a variant of a stock monster)
   named *role label + proper name + epithet*, carrying a named key. So
   the recurring label is one functional word, not six invented names,
   and the court-rank scheme in the design is the wrong read of it. **The
   role word is settled: "the Keybearer".** Still hers: each guardian's
   proper name and each key's. The Cellar King, the seal and the first
   lock (floor 3 to 4) are settled. See `DECISIONS.md`, 2026-10-03.
2. **The elemental campaign's remaining open decisions**
   (`design/elemental-and-status-effects.md`). **Settled 2026-10-03:** the
   hero's resistances live in **two** places — the pack's `player` block as
   a base (`player.resist` / `player.immune`) and **worn gear on top**. The
   gear half dodges the ADR entirely, because Blueprint's closed key sets
   govern *enemy* records, not items. Still owed: the damage resolver, the
   status store and whether it saves across a reload, and whether a status
   is a Blueprint field or a pack block.
3. **The language packet's Foreman count and model**
   (`11-open-decisions.md` item 7). **Settled 2026-10-03: one foreman per
   campaign, slices in sequence, MiniMax M3.1, budget 8, integrator
   reviews every diff.** The deciding reason: the descent block's two halves
   share `maplab.py` and `web/packaged.html`, so parallel foremen would
   conflict on the same files anyway.

**Closed 2026-10-03:** the language packet's disposition read. Rylee
approved GO WITH CONSTRAINTS ("Approved. Go"). That releases the gate and
authorizes the earned scope only — the optional build-time source layer,
whose first slice (Blueprint) is already built and trialled. It does
**not** authorize a new runtime, event sourcing, a logic engine, a plugin
system, a kernel, broad pack migration or a new public pack contract;
those stay deferred until there is a second real consumer.

"Should rumors read pack canon?" (raised 2026-09-25) was already
true: `saga.system_prompt` has carried the pack's `logbok.md` since
2026-08-31. The orchestration plan's "pack-blind" note was wrong; a
test now pins it (`test_rumor_prompt_carries_pack_canon`).

Closed 2026-09-25 (see `DECISIONS.md`): munr kept separate (D5
superseded); the local test packs deleted; commit `948df78` accepted as risk.

## Known debt (small, safe to pick up)

- **Kitchen screen shows town leftovers.** The woven Act 1 player renders
  the Whisper button, an `HP 0/0` bar, and an empty town canvas above
  the kitchen (seen in headless Chromium, 2026-09-25). Cosmetic; the
  kitchen loop itself plays clean.

- `docs/guides/accessibility-contract.md` and `docs/guides/brain-socket.md`
  kept the demo game's name in a few places until the 2026-09-29/30 sweeps;
  both are now game-neutral, and the name sweep is recorded in `DECISIONS.md`.

Closed 2026-09-26: `norns chat` voice drafting looping (the WP5 voice
file repeated itself). The draft seam now dedupes repeated sentences —
see `ROADMAP.md`. Left open, found while fixing it: the interview writes
the first speaker's draft to the pack root's `voices/<name>.md` while an
acts-shape pack's live voice file is the region one.

## Branches

| Branch | Status |
|---|---|
| `main` | trunk; land by PR (convention — protection does not require reviews) |
| `oa/old-main-20260920` | **gone** (2026-10-03): the local-only snapshot of main from 2026-09-19 no longer exists on this machine or on the remote, and no reflog entry survives. Cause UNKNOWN — not deleted by the 2026-10-03 session. Rylee should confirm nobody needs it; if they do, the 2026-09-19 main is still reachable in the commit graph. |

## Known protected work

| Item | Path / scope | Source of truth |
|---|---|---|
| Play-Nice adoption pin | `0cee0652fb6f13c440b1fd9cc5d78fd87cdca8ad` | `.project/contracts/adoption.yaml` |
| Sample world pack (Emberfield) | `worlds/sample-world/` | `worlds/sample-world/` |
| Three lore packs | `worlds/lore/{norse,historical-event,norse-runes}/` | each pack's `LICENSE.md` |

## Verification entry points

```bash
# Gate - must match CI (.github/workflows/ci.yml)
uv sync --group test
uv run --group test ruff check src tests scripts
uv run --group test pytest -q
python3 scripts/check_public_surface.py

# Pack integrity
uv run --group test norns validate --pack worlds/sample-world

# Session-start health
uv run --group test norns doctor   # set VEFR_LIVE_URL to check a stack
```

Run the full gate even for docs-only commits: `tests/test_pack_neutrality.py`
audits `README.md`, `AGENTS.md`, `ROADMAP.md`, and `docs/`.
