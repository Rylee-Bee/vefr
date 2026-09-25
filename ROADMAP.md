# vefr - Roadmap

> The three Norns weave fate at the well beneath the world tree -
> not one fixed fate, whichever one is given them. This is the
> ladder from a tool built for one story, playable - to a tool
> anyone can point at their own.

## Landed

- [x] **Weave from the web: a phone user with no terminal can make the
      shareable file** (2026-09-25): `ratatoskr weave` was terminal-only.
      The packaging core moved out of `cmd_build_web` into `weave_html` +
      `build_web` (the CLI keeps calling it, output byte-identical), and the
      served workshop's Desk grows a "Make shareable file" button:
      `POST /api/builder/weave` builds the current world (same `pack_dir`
      resolution as the other builder routes) into a server-owned dir
      (`VEFR_WEAVE_DIR` or `app_home()/dist`), one at a time (409 on a
      concurrent weave), returning `{name, size_bytes, built_at,
      download_url}`; `GET /api/builder/weave/file/{name}` serves that file
      as an attachment behind a strict filename regex + in-dir resolve
      (traversal refused). The page shows "Weaving…" then "Ready · N KB",
      then a Download link and — where `navigator.share` supports files — a
      Share button (>=44px targets, visible focus, status as words, 390px).
      Tests: `tests/test_builder_weave.py` (metadata + real download,
      traversal refusal, 409 lock, CLI/shared-core byte parity). Gates:
      ruff clean; pytest 488 passed / 3 skipped; sample-world validate ok;
      public-surface clean (401).

- [x] **Local test packs removed** (2026-09-25): owner ruling — the
      gitignored `worlds/rylee-alpha-world/` and `worlds/kitchen-playtest/`
      were test artifacts; deleted from disk (default pack now resolves to
      `sample-world`). DECISIONS and CURRENT corrected from "parked".

- [x] **Weave keeps acts for relative out-of-root packs; rumor canon pinned**
      (2026-09-25): `ratatoskr weave --pack ../<repo>/worlds/<pack>` silently
      dropped `VEFR_WORLD.acts` (the relative path was joined under
      `worlds/` and the load error swallowed), so the player's act router
      never saw `ruleset: cooking` and opened the town instead of the
      kitchen. `cmd_build_web` now resolves path-style packs to absolute.
      Regression: `test_weave_keeps_acts_for_relative_out_of_root_pack`
      (fails before, passes after). Also pinned: every rumor's system prompt
      carries the pack's `logbok.md` (`test_rumor_prompt_carries_pack_canon`;
      true since 2026-08-31, previously unpinned).

- [x] **Resolve the open-issue list** (2026-09-25): (1) the CI `--ignore`
      flags and the "informational" pytest step named two Storyteller test
      files that exist nowhere in the tree or history, and a tracker item
      (#50) that is no longer reachable; the informational step failed
      silently on every run. All removed: CI and the docs now run plain
      `pytest -q`. (2) D6 finished: engine tests and the rulesets guide
      example use neutral fixture fiction, no game-pack names. (3) The
      2026-09 model-benchmark reports and harnesses moved to
      `.project/archive/model-benchmarks-2026-09/` (only consumers were each
      other). (4) Owner rulings recorded in DECISIONS: the sibling engine repo kept separate (D5
      superseded), alpha pack parked, old art commit accepted. CURRENT.md
      updated; one open design call remains (rumor path reads no pack canon).

- [x] **Green main + orientation refresh** (2026-09-25): `78fa0f8`
      named the sibling engine in AGENTS.md and tripped
      `test_no_historical_package_names` (CI red on main). AGENTS.md now
      points to `.project/DECISIONS.md` (outside the audited roots), which
      records the not-synced rule and flags D5 as unreconciled.
      `.project/CURRENT.md` rewritten: the phase table (engine at Act 2, the game
      pack at Act 1 awaiting the owner's taste-pass), where the out-of-repo
      plan lives, open owner decisions, small safe debt, and a gate command
      that matches CI. Gate: ruff clean; pytest 0 failed; public-surface
      clean; validate ok.

- [x] **Act 2 increment 1: the Desk ruleset - is_true finally consumed, the
      world knows its own stories** (2026-09-22): Phase 2 of the game plan
      begins. Engine: `desk.py` (verify / print / facts / prompt_lines -
      deterministic, no model calls; knowledge DERIVED from the session
      journal on every read, no separate store to corrupt); rumors and NPC
      lines now thread the session id into their prompts, so
      `WHAT THE WORLD KNOWS NOW` (confirmed / debunked / printed) rides in
      every later generation; routes `POST /api/desk/verify`,
      `POST /api/desk/print`, `GET /api/desk/facts` (added under the
      approved plan; AGENTS ask-first noted in this entry); pack contract
      gains the per-act `desk` block (headlines validated >= 2 when
      `ruleset: desk`). Player: the packaged player grows a Desk screen
      (listen -> trust/doubt -> print -> what-the-world-knows), fully
      client-side like the rest of the single file, reusing the honest
      fallback chain (live schema -> woven pool -> composer -> fragments).
      Tests: test_desk.py (8 server pins incl. prompt injection both ways)
      + desk_harness.mjs + test_desk_loop.py (5 play pins; whole loop <= 6
      clicks). Weave now resolves out-of-root packs by path for pool builds
      (fixes tmp-pack weaves; BJ repo weaves unaffected). dev-guards: the
      desk pack joins the axe gate. Gates: a11y no serious/critical on
      sample+kitchen+desk weaves; visual drift 0.0000%; ruff clean; pytest
      2 failed (documented model-up env pair) / 474 passed / 1 skipped;
      public-surface clean (394); validate ok.

- [x] **Dev-guards: the tooling gate (owner directive: "implement them and
      continue development")** (2026-09-22): the MIT-tooling survey's top four
      land as one guard workflow + hardening. (1) `dev-guards.yml`:
      actionlint 1.7.12 (checksum-verified release binary) + zizmor 1.30.1
      (pinned `uv tool run`) over `.github/`; axe-core 4.13.0 gate (vendored
      MPL-2.0, `scripts/a11y_check.py`, real chromium via the existing
      playwright test dep) over BOTH woven players (sample + kitchen
      fixture); visual regression (`scripts/visual_regress.py`) — stdlib
      PNG decode (zlib + scanline unfilter, zero new deps; pixelmatch
      evaluated and set aside to honor keep-deps-short) against a committed
      baseline, `VISUAL_UPDATE=1` for deliberate redesigns. (2) zizmor's
      first run found seven live findings in OUR workflows; all fixed or
      justified: `persist-credentials: false` on ci/secret-scan/security
      checkouts, dependabot `cooldown: 7d`, screenshots.yml keeps its push
      token under a justified ignore, publish-image's `workflow_run`
      (main-branch-filtered, post-merge SHAs only) under a justified
      ignore. (3) the kitchen harness moved from my hand-rolled stub DOM to
      **jsdom** (MIT, dev-only `package.json`; happy-dom evaluated and
      rejected with evidence: it does not execute inline scripts via
      document.write). (4) `tests/fixtures/make_kitchen_pack.py` factors the
      neutral kitchen fixture out for CI gates. New: THIRD_PARTY.md
      (vendored/dev-only provenance). Local evidence: a11y gate no
      serious/critical on both woven players; visual drift 0.0000% vs fresh
      baseline; actionlint clean; zizmor "No findings" (2 ignored, 10
      suppressed); ruff clean; pytest 2 failed (documented model-up env
      pair) / 461 passed / 1 skipped; public-surface clean (384); validate ok.

- [x] **Act 1 increment 1: the kitchen ruleset v0, act-runner router, and the
      pleasant-loop harness** (2026-09-22): Phase 1 of VEFR-GAME-PLAN begins per
      the owner's Act-1 directive (a cooking act that wakes, serves, and prints
      its first page). Engine: per-act `cooking` contract block (pantry / tickets /
      morning_length / headlines / optional opening + byline) loaded by both
      loaders,
      shape-validated by maplab (orders must reference real pantry ids; every
      ticket needs the customer's voice; headlines must be a real choice),
      echoed by inspect. Player: `web/packaged.html` gains a per-act screen
      router (`startPlaySurface`) and the kitchen - tickets arrive as spoken
      notes (reading them is the game), assembly resolves by deterministic set
      equality, wrong burritos get kind beats never slaps, tickets set aside
      wait without penalty (no timers anywhere: `setInterval` absent from the
      template), and the morning closes with the player's first editorial
      choice printing page 1 of the paper (masthead, headline, pack byline,
      honest body, pack creed, "more mornings soon") plus a sleep/wake replay
      nudge. Tests: tests/test_cooking_contract.py (contract pins) and
      tests/test_kitchen_loop.py + tests/fixtures/kitchen_harness.mjs - a
      stub-DOM harness that EXECUTES the woven file and plays a whole morning,
      asserting journal order, kind beats, the printed page, a ≤4-clicks-per-
      ticket budget, and timer absence: the CI-enforceable half of the
      pleasant-loop protocol (VEFR-ACT1-SPEC §9). Playtest pass 1 (harness,
      offline): 8 clicks for a 3-ticket morning; fix-forward landed in the same
      increment (set-aside beat line was overwritten by the morning-over line;
      both now read). Weave bakes the acts contract (verbs/floor/tone/ruleset/
      cooking) so packaged packs carry their law; cli's default tagline lost its
      last private-canon string (the old private tagline, now the engine
      tagline; the canon list grew the string so the guard proves it stays
      gone - and caught this very entry quoting it, twice).
      Gates: ruff clean · pytest 2 failed (both documented model-up env) /
      461 passed / 1 skipped · public-surface clean (381) · norns validate ok.

- [x] **Phase 0 boundary: private canon out of the engine, pack-law contracts
      in, guards into code** (2026-09-22): owner-approved Phase 0 of
      VEFR-GAME-PLAN-2026-09-22 (vision interview Q1-Q8 is the authority).
      (1) Private-game assumptions removed WITHOUT touching the Norse
      identity: the engine tagline/PURPOSE (the old private tagline is gone;
      now "a rumor engine for playable worlds" + "the loom is strung; the
      world provides the thread"), gold-canon prose in journey.py/runes.py,
      the hardcoded 'awed'-phase sighting in town.js, starred stefna letters
      routed under a pack phase name (now their own `## letters` heading), and
      CSS/encounter lines keyed by phase/bond NAMES (now positional: the pack's
      culminating phase wears the accent via data-culm; encounter lines key by
      phase index). (2) Pack-law contract (world.py docstring): per-act `floor`
      (costume|story|stakes; default costume = today's behavior exactly),
      `tone` (the ridiculous-literal dial, carried in the storyteller prompt),
      `ruleset` (default ambient), `verbs` (the act's own action vocabulary -
      when declared it replaces the costume verbs in the HUD AND the
      /api/combat/action whitelist); `enemies/bosses/transitions` now
      shape-validated. All optional; every existing pack loads unchanged.
      (3) Guards extended into engine code: canon-strings list carries the
      removed strings (it caught this very entry's first draft quoting them -
      the teeth work); tests/test_phase0_boundary.py pins the boundary in CI
      (no pack phase names in engine behavior, no private taglines, verb/
      floor/tone/ruleset validation, tone-dial prompt carriage).
      (4) Function preserved: ruff + pytest + public-surface + norns validate
      green; sample-world untouched.

- [x] **web: setup is a choice, not a wall; the URL join can't double**
      (2026-09-22): two player-facing defects in `web/packaged.html`,
      both hit live during the WP5 playthrough. (1) Every POST joined
      `llmUrl + '/v1/chat/completions'`, so the config URL as the
      placeholder itself shows it (`...:11434/v1`) produced
      `/v1/v1/chat/completions` and a dead 404 — the join now lives
      once in `chatEndpoint()` (idempotent over base, `/v1`, trailing
      slashes, pasted full endpoint). (2) First-run setup hard-gated
      `alert('both URL and model are required.')`, with no way past it
      even though the woven pool exists precisely to carry offline
      play — both-blank now saves as a remembered offline choice
      (`configured: true`, older saves still pass), half-filled still
      warns (one without the other can never reach an endpoint), and
      `llmPost()` rejects straight into the pool/fragment fallbacks
      instead of fetching a relative URL. Pinned by
      `test_chat_endpoint_normalizes_the_config_url` and
      `test_setup_gate_allows_offline_play`.

- [x] **chat: a dead endpoint falls back, never crashes the interview**
      (2026-09-22): every model call in the interview retries twice
      before falling back to scaffold/placeholder — except transport
      failures never reached that loop: `generator._completion` wraps
      httpx timeouts in `GeneratorUnavailable`/`GeneratorFailed`, which
      none of the four retry loops caught, so a slow brain killed the
      interview mid-run (the `draft()` docstring's "never a crash
      mid-interview" was false for the one failure most likely to hit a
      first-time author). Found live during the WP5 owner walkthrough;
      both vefr transport exceptions now take the retry → fallback path
      in `draft`, `draft_theme`, `propose_map`, `propose_face`, pinned
      by `test_dead_endpoint_falls_back_instead_of_crashing`.

- [x] **weave: acts-shape packs bake the resolved world** (2026-09-22):
      `cmd_build_web` baked the raw `world.json` root, but acts-shape packs
      keep `town`/`speakers`/`creed` under `acts/<id>/` — so a woven file from
      such a pack drew a blank town (`setupTown` TypeError, bootstrap aborted
      before the verbs attached), exposed no `npc:` pools (`pool.py` read the
      long-dead root `speakers`), and fell back to the default tagline. Weave
      now merges `load_pack()` over the raw root (same shape the CLI's live
      path resolves), `pool.py` takes speakers from `current_act()`, and the
      pool fixtures were converted to acts shape — which is itself the
      regression test. Found by the first-ever browser stranger-test of a
      woven file (WP7).

- [x] **weave: template resolution works from a pip-installed engine**
      (2026-09-22): `cmd_build_web` resolved `web/packaged.html` only via
      the source-checkout or `VEFR_HOME` layouts, so a pack author running
      `ratatoskr weave` from their own repo (installed wheel) hit
      FileNotFoundError before any weaving began. The wheel now ships the
      template as package data (hatch force-include → `vefr/web/`),
      `_template_candidates()` covers checkout → package data → VEFR_HOME
      in that order, and regression tests pin both the candidate shape and
      the packaging config. Found while weaving the demo from the pack
      repo (WP7).

- [x] **WP6-wrap: templates + brain-socket example neutralized** (2026-09-22):
      owner chose "fix now" — the two copy-paste storyteller tests plus their
      sample fixture under `tests/templates/`, and the persistent-memory
      example in `docs/guides/brain-socket.md`, were the last tracked
      surfaces quoting private-pack names. All now use engine-neutral
      caretaker/forge and market-lane examples; self-contained tests stay
      green, guards clean (378 — the +1 is `sample-scene.json`, now tracked
      and scanned per D6, which was untracked during WP6's guard run).

- [x] **WP6 / D6: fixture content follows ownership - neutral sample
      in the engine, seam for pack scenes** (2026-09-22): the
      engine-owned audition fixture was a private pack's scene. D6:
      it moves to the BJ pack repo, and the engine now ships
      `tests/fixtures/storyteller/sample-scene.json` as the
      `norns storyteller-test` `--scene` default and the docs
      showcase (regenerated from real packet output). The loader
      gains `VEFR_STORYTELLER_FIXTURES` - a PATH-style dir list
      searched before the engine's own fixtures, so pack-supplied
      scenes win on id collision. The public-surface guard no
      longer skips `tests/fixtures/storyteller/` (that skip existed
      only for the moved fixture); engine tests repoint at
      `sample-scene`, and the BJ-content assertions move to the BJ
      pack's own test suite.

- [x] **example.env: interface port corrected, spark modes made explicit**
      (2026-09-22): the Interface Translator block still said "Port 8085
      is the unambiguous default" with `#VEFR_INTERFACE_URL=…:8085` —
      stale since WP2 moved the translator :8085 → :8087 (vision took
      :8085). Value and comment now say :8087, matching
      `interface.py:174` and `test_interface.py`. The Spark comment now
      names both documented modes (:8082 no-bundle default, :8083
      bundled image → `docs/guides/bundled-brain.md` carries both
      columns). Recon finding recorded: a suspected `spark.py`/:8082 vs
      `volumes.py`/:8083 contradiction is NOT one — the three writers
      are each self-consistent per mode, so no port code changed.

- [x] **Docs restructure: three-section README + canon guard on root
      docs** (2026-09-22): README grew to 484 lines mixing philosophy,
      world-authoring, and ops. Restructured to three pillars - "Open
      and play" (60-second start), "Build a world" (bones/flesh
      contract, pack layout, Design/Hero's-Journey + lore-pack tables,
      Surface), "Run the engine" (container, config, compose) - with
      the intro relinking to the new anchors, ~200 lines out. Moved the
      env-var table into GETTING_STARTED "What you need" with defaults
      corrected to code truth (`VEFR_MODEL=gpt-oss-20b`,
      `VEFR_LLAMACPP_URL=:8081`, `OLLAMA_URL=:11434`,
      `VEFR_KEEP_ALIVE=1m`), reordered GS to §1 get the code → §2 open
      and play → §3 make your own world → §4 sound check → §5 CLI →
      §6 shipping → §7 API (CONTRIBUTING anchor updated), relocated the
      phone-as-backend section to `docs/guides/install.md`, and cut
      count-free CLI prose from `cli.py --help`, `AGENTS.md`, and GS
      (`--help` is canonical). Scrubbed the one private-game canon line
      from README and extended `test_pack_neutrality` to audit root
      `*.md` + `LICENSE` with whitespace-normalized matching - RED
      captured pre-scrub (README:435), green after. Kept the
      worked-example lore tables (tight) and the pack file list;
      module tree compressed to pointers at `src/vefr/*.py` docstrings
      + `brain-socket.md`.

- [x] **screenshots workflow: first-ever green run** (2026-09-22): the
      auto-capture workflow had never passed — 7 straight failures
      since wiring. Every capture step actually succeeded (artifacts
      uploaded, ~1.5 MB of PNGs); the run was failed only by
      `setup-uv@v5`'s post-step, which prunes the uv cache before
      saving. The prune hung 5 minutes and exited 2, so the cache
      never once saved (every restore missed "No GitHub Actions
      cache found") — pure cost, sole failure. Aligned screenshots.yml
      to the exact pins `ci.yml`/`security.yml` already use and pass
      with: setup-uv v10.1.0 (prune-cache defaults false, node24),
      checkout v7.0.1, upload-artifact v7.0.1 — all SHA-pinned like
      the rest of the fleet.

- [x] **The creed: pack field rename + sample-value sanitize** (2026-09-22):
      the pack contract's `gold_rule` field carried one author's game
      term into the engine, and the sample-world value was that game's
      canon line. The field is now `creed` everywhere - contract
      (`world.py`), loader, inspect, maplab, spark prompt, API, weave
      tagline, web labels, CSS class, docs, fixtures - read through one
      owner (`creed_from`) so `gold_rule` survives as a read-fallback:
      packs written before the rename keep their line, and maplab
      writes them back as `creed` on the next save. Sample-world's
      value is now engine-neutral ("Walk gently; the town remembers.")
      across `world.json`, `logbok.md`, and `world-tree.md`. Added
      `test_creed_reads_the_legacy_field_name` pinning the alias, and
      the local canon-strings guard now bans the old line and term
      (list never ships - audit stays local-only by design). Gates:
      ruff clean; pytest 427 passed / 1 skipped (2 known
      model-dependent env failures); public-surface clean (377).

- [x] **World-creation guide: interview to playable HTML** (2026-09-22):
      drove `norns chat` end to end against the bundled Spark as a
      first-time author would - 15 prompts, exit 0, a valid pack in
      25 seconds. Both gated fallbacks captured verbatim (theme kept
      the scaffold's colors; the map proposal failed its hard
      validation gate twice and the proven layout held). Extended the
      map through `norns build-map` from a run-length segments file
      (+1 row, unforced - validation gated the write), re-validated
      ok, and wove a 10-line pool (`rumor:dusk`, `rumor:dawn`,
      `letter`, `forge`) into a 37.9 KB single-file HTML. Wrote
      `docs/guides/world-creation.md` from that capture: the full
      prompt sequence, what blank keeps, the fallback messages, the
      segments format, cleanup, troubleshooting - linked from
      `GETTING_STARTED.md` and the `AGENTS.md` references. Gates:
      ruff clean; pytest 425 passed / 2 skipped (2 known
      model-dependent env failures); public-surface clean (377).

- [x] **Bundled fleet complete: Vision tenant on :8085** (2026-09-22):
      docs promised a 4-model fleet; the image carried 3 — SmolVLM2 was
      never bundled (the docs-vs-reality gap). Added
      `ggml-org/SmolVLM2-500M-Video-Instruct` Q8_0 (417 MB) + its mmproj
      (104 MB) — SmolVLM2's only official 500M checkpoint, API-verified
      URLs + size guards, one image layer per model so editing one fetch
      can't re-fetch the fleet, and a build-time `--mmproj` assertion so
      a multimodal-less llama-server can never ship. `start-bundled.sh`
      launches vision on :8085 (health loop now 8083–8086);
      `VEFR_VISION_URL` baked into the image + compose/quadlet parity.
      The Interface Translator's default moved :8085 → :8087 — its own
      stated invariant is "never shares a default port with another
      conceptual service", and vision is now :8085's tenant (its docstring
      records the move). README/guide size claims corrected to the real
      546 MB. Verified local E2E: image in → description out on :8085,
      four brains + engine green; ruff clean; pytest 425 passed /
      2 skipped / 2 known model-dependent env failures; public-surface
      clean.

- [x] **NPC seed fallback survives the fail-closed translation** (2026-09-22):
      with the brain down, `POST /api/npc` returned a 404 leaking
      `[Errno111] Connection refused` instead of the canon seed line the
      contract promises (`npc.py`: "If the model is unreachable, a seed
      line speaks instead"). Cause: `_completion` translates httpx failures
      into `GeneratorUnavailable`/`GeneratorFailed`, but `generate_line`'s
      except tuple only caught raw `httpx` errors — the old test injected
      the error *below* that translation seam, so it stayed green while
      live runs broke. Surfaced by the WP2 Meera (brain-down) drill. Fix:
      catch both translated errors in `generate_line` + a regression test
      pinned at the production seam. Verified live: world/journal → 200
      with brains dead, npc → 200 `source:"seed"`; ruff clean; pytest
      425 passed / 2 skipped / 2 known model-dependent env failures.

- [x] **Container runs as root: bind mounts writable again** (2026-09-22):
      the non-root `USER vefr` (uid 999) could not write host-owned bind
      mounts under rootless engines — host uid 1000 maps to container uid 0,
      so the mount appears `root:root 755` and uid 999 gets EACCES. Observed
      live on the deployed quadlet: `POST /api/rumor` → 500
      `PermissionError: /app/data/journal.tmp`. Removed `USER`/`useradd`
      from the Containerfile; an in-file comment records why and forbids
      re-adding `USER` without solving bind-mount ownership. Under rootless
      engines container root *is* the unprivileged invoking user, so no real
      privilege is gained or lost; the named-volume compose flow was never
      affected. Verified: rootless docker + `:Z` bind write OK; ruff clean;
      public-surface clean; pytest 425 passed with the one known
      model-dependent env failure.
- [x] **Bundled-brain image build fixed + E2E verified** (2026-09-22,
      `a895898`): llama.cpp b5530 is now built from source inside the
      Containerfile (pre-built Linux release binaries are no longer
      published; static libs + `libgomp1` in the final image), and the three
      model URLs were corrected to API-verified paths with build-time size
      guards so an error page can never pass as a model — spark Qwen3-0.6B
      (`:8083`), storyteller Qwen3-1.7B (`:8084`), embeddings bge-m3
      (`:8086`), 2.0 GB baked. `docker compose up` now yields a playable
      game with no external LLM. Proven end-to-end: all three brain ports
      come up and `POST /api/rumor` returns a RumorCard generated by the
      bundled Qwen3-1.7B on CPU.
- [x] **Sample-world CC0 art swap** (2026-09-21): replaced the bundled
      non-redistributable tileset (1,131 PNGs) in `worlds/sample-world/assets/`
      with Kenney CC0 tiles under `assets/kenney/`; corrected `LICENSE` and
      `THIRD_PARTY_NOTICES.md`, which had mislabeled that art as CC0. The demo
      town renders its map in code, so gameplay is unaffected (`norns validate`
      green; `ruff` clean).
- [x] **Fleet Storyteller role + benchmark** (2026-09-14,
      `ab1695c`): the fleet storyteller capability — an anti-agentic
      narrator. `src/vefr/narrate.py` receives an authoritative
      action result plus bounded context and returns prose only (no
      tools, no mutation, no canon invention); fail-closed
      (`StorytellerUnavailable` / `StorytellerFailed`). Template
      as data in `templates/storyteller/narrate.json`
      (storyteller-narrate-v1: authority > template > lore >
      prose precedence, ambiguity preserved, player agency
      preserved). New CLI `vefr-story` (--json, --fixture, --model,
      --endpoint). Benchmark in `bench/storyteller/`: 25
      single-turn cases + 5 multi-turn sequences with hard
      must/must_all/must_not gates, non-contradiction continuity,
      and a replay mode. Winners (CPU llama.cpp):
      `smollm3-3b-q4` 25/25 gate, 5/5 sequences, 100%
      continuity, 11.4 tok/s (retained as storyteller head);
      `ministral-3-3b-q4` equivalent at 11.3 tok/s.
- [x] **Interface Translator + benchmark** (2026-09-13/14,
      `175d771` + `772677b`): `src/vefr/interface.py` — a tiny
      strict-intent brain mapping natural language to the engine's
      canonical action vocabulary (attack, console, hurl, strike,
      observe, speak, move) via strict json_schema + pydantic
      validation; deterministic clarification on missing args,
      fail-closed everywhere, no world mutation. Template as data
      in `templates/interface/intent.json`. Benchmark in
      `bench/interface/`: 29 deterministic cases; smaller models
      (qwen2.5-1.5b, qwen3.5-0.8b) fail the safety gate on unsafe
      false-positives; `qwen3.5-9b-mtp` wins (100% schema-valid,
      strongest safe-rate) as the reference head.
- [x] **Lorekeeper slice: `vefr-lore` add/ask** (2026-09-13,
      `f0d6612`): `src/vefr/lore_shell.py` — structured durable
      truth (`facts.jsonl` authoritative, `index/` derived),
      bge-m3 embed client via `VEFR_EMBED_URL`, pure-Python cosine
      retrieval, fail-soft on embed outage. No generative path.
- [x] **Small Model Finals + qualifier round, 2026-09 bench** (2026-09-13,
      bench/finals commits + local `bench/reports/` evidence): two
      skimmable rounds of the small-model bench campaign, plus the
      qualifier campaign that followed.
      (1) **Quick finals** (`bench/finals/DECISION-PACKET.md`,
      CPU-only, Q4_K_M): *Worlds* default = **Qwen3 1.7B**
      (6 PASS/8 PARTIAL vs LFM2.5-2.6B's 4/10), fallback LFM2.5;
      *VEFR* default = **Phi-4-mini** provisional (11/12 at 3x the
      speed of Ministral-3-3B's 12/12), fallback Ministral 3 3B.
      (2) **Qualifier campaign, suite 0.4.1** (`bench/reports/
      QUALIFIER-TLDR-2026-09-13.md`): 27 models x 53 tasks, every
      run now completes (the stuck runs were three harness bugs,
      zero model faults); backend is observed per run, not assumed;
      all latencies contended (resident 27B holds the VRAM) and
      never comparable to historical idle numbers. Standings
      (pass%): top = qwen3-1.7b 76, lfm2.5-2.6b 70,
      ministral-3-3b 68, falcon3-3b 66; weak = gemma3-1b 42,
      qwen3.5-0.8b/-2b 30/28. Honesty notes carried forward:
      phi-4-mini 64.2% here differs from its historical 100/100
      (different production-path set), and legacy backend
      provenance is UNKNOWN. Raw per-run evidence in
      `bench/runs/` (`index.json` is canonical).
- [x] **The Foyer sits in the house's own column** (2026-09-15): the
      launcher used to stretch full-bleed edge to edge while every
      other room sits in a centered ~680px readable column, and the
      first-walk rail (pinned top-right of the room) hovered over the
      foyer's right edge. The Foyer now keeps the same centered
      column as the Desk and the boiler room
      (`max-width: min(680px, calc(100vw - 32px))`, auto margins), so
      the walk rail clears the cards on desktop and the landing reads
      like the rest of the house.
- [x] **The Foyer — a launcher landing, the door you step through
      first** (2026-09-15): the studio now opens onto The Foyer, built
      like a game launcher: the project on the table (the real current
      world from `/api/world`, with act, phases, and an "enter the
      house" door into the Desk), the pantry (every real pack from
      `/api/builder/worlds`, honestly marked "in the pantry — ask the
      keeper to set VEFR_WORLD" since the engine is bound to one world
      per running house; no fake switching), what the house remembers
      (kept lately from the real vault, starred lately from the real
      journal, spoken lately from the folio threads and watch
      whispers), and quick options at the mantel that mirror the
      boiler room's contracts (hearth sound and motion via
      `VEFR_PREFS`, walk again + sheet via the first walk, boiler room
      door). Every panel fetches real endpoints with honest
      loading/empty states; nothing is invented. The Foyer is the
      first placard and the default landing route (a `#screen` hash
      still wins).
- [x] **The walk walks you — after each step, onwards to the next
      room** (2026-09-15): the housewarming used to stall at the
      first popup because the folio (bell and faces open it) covered
      the shelf and nothing guided you onward. Now each walk step
      knows its room; when a step truly completes, Ratatoskr tugs
      your sleeve and walks you to the next step's room — the folio
      steps wait until you close the folio, then set off, the rest
      move after a short beat, always with a ferry note. The shelf
      (and any room, including the Foyer) also shows a "walk me to
      {Room} →" button for the current step, hidden when you're
      already there. The step still only completes when the real
      action fires — the walk guides, never invents progress.
- [x] **The workshop becomes rooms: full scene frame, the
      household, and the keepsake Hall** (2026-09-15): the UI's
      chrome is gone - the shell is now a room scene with a hanging
      sign, a low shelf of ≥44px carved placards, a candle lantern
      for connection (lit when the storyteller is reachable, cold
      with a plain sentence when not), a world-phase candlelight
      tint, and the mood-note whisper. Nine screens: the seven rooms
      plus The Hall (real `/api/starred` + vault + journal stars) and
      plain Settings. The household lives here - one engine, many
      faces: The Storyteller (Desk), The Cartographer (Map),
      The Keeper of Faces (Folks), The Hoard-Keeper (Vault),
      Urðr (Chronicle), The Rune-Carver (Casting), Skuld (Archives),
      Ratatoskr (Hall). Every room has a "tended by" line and a
      speaking folio wired to `/api/builder/chat` with per-resident
      role templates (history owned by the page, `{message, history}
      → {reply}`), plus the Storyteller bell on the Desk. Squirrel
      ferry language for loading; motion off by default; all
      interactive targets back to ≥44px (the 40px/32px regressions
      are fixed). Engine stays story-agnostic; interiors carried
      forward from the warm pass. Reference provenance in
      `design/UI-REFERENCES.md` (RPGUI zlib, A Dark Room MPL-2.0,
      Twine/SugarCube per-theme, gameuidatabase.com taste).
- [x] **Rooms become benches: warmth, real builders, and rooms that
      use the screen** (2026-09-15): a second pass on the room scene -
      hearth glow, candle flicker (dead under `motion=off`), warmer
      wood, parchment folio, wax-seal mark, per-room ambience lines,
      and Ratatoskr's ferry note when the squirrel acts. The Map Room
      becomes a survey bench: per-region survey readouts (dimensions +
      ground census read off the real map), every mark a ≥44px door
      into the folio ("what is 'g' in town?"), a "deepen a landmark"
      tool wired to `/api/builder/enhance/map`, and a real pack-check
      (`/api/builder/validate`). The Vault becomes a forge bench:
      "ask the forge" (real model roll), shape the draft by hand on
      the anvil, keep it into the vault (`POST /api/vault`, new
      `VEFR_API.vaultKeep`), or deepen a kept thing
      (`/api/builder/enhance/item`); model-less failure is honest
      ("the forge is cold"), not a red error. Settings is no longer
      a plain hall: the boiler room has its own smith, Völundr, with
      the same folio chat as every room and role templates tuned to
      the studio itself (which reading mode, walking the motion
      setting, setting the room up for an easier day). Layout fixes: rooms span
      the full screen with centered readable columns (Chronicle,
      Archives, Hall, Map, Vault, Casting, Folks); Settings becomes a
      responsive grid (was a scrunched 580px column); deep Archives
      levels are readable (10-11px mono → 12-12.5px) with the raw
      truth contained; loading/empty states center everywhere (the
      Chronicle squirrel no longer veers left). Settings now drives
      `window.VEFR_PREFS.set(...)` - prefs.js is the one canonical
      owner of `data-prefs` tokens, so the motion-off a11y floor
      actually works in the workshop (the old `data-motion` attribute
      the foundation ignored is gone).
- [x] **The Map Room gains the drawing table - a map maker with no
      markdown** (2026-09-15): a storyteller doesn't need to know
      glyphs to make a map. The table reads the pack's real legend
      into labeled ink pots ("solid", "open ground", "marked",
      "sanctuary" - derived from the pack's own solid/deco/
      sanctuary_tiles data, never invented), a paintable 44px-cell
      grid with a proper roving-keyboard grid surface (arrows move,
      Enter inks), a live ink-line census, and three honest actions:
      "reset the ink" restores the pack's ground; "sketch new land"
      calls the new `/api/builder/map/propose` route (the same
      model-drafted, `maplab.validate`-gated run-length pipeline as
      the `norns chat` interview - proposal only, never writes to
      the pack, honest message without a model); "keep this sketch"
      posts the sketch as a real vault keepsake item (kind
      "sketch"). Drafts persist per world+region in localStorage so
      the table remembers your ink between visits, and "ask the
      Cartographer about it" prefills the folio. Two new tests
      (`tests/test_map_propose.py`) assert the route returns a
      validated grid and never mutates the pack, plus the honest
      no-model path. New public route `POST /api/builder/map/propose`
      (engine surface, flagged per Ask-first).
- [x] **The Housewarming — a first walk, taught by doing, and a
      broadsheet that stays** (2026-09-15): the first time the
      studio opens with no walk on record, Ratatoskr pins a short
      note under the sign. Five steps, one real action each, in five
      rooms: ring the bell, press the ground once, press a leaf,
      open a face, look out the window. Each step completes only
      when the real button truly fires (the same event hooks as the
      keeps and squeaks) — nothing is invented, no fake progress.
      Progress persists in `vefr.walk`; skipping is one press;
      "walk the house again" and "open the sheet" sit under
      Settings so both stay callable any time after setup. The
      tucked-in extra is a broadsheet — "How to read this house" —
      one line per room plus the three rules of the house, as a
      real dialog (focus-in, Escape closes, focus returns). The
      walk is model-agnostic on purpose: it works whether or not a
      brain is attached (the bell answers however the lantern
      honestly does). A11y held: real list/dialog semantics,
      ≥44px targets, aria-live step announcements, zero motion,
      plain English only. Verified 412 passed, 2 skipped.
- [x] **The household keeps, invites, listens, and sounds only when
      asked** (2026-09-15): the studio's ten wants, all landed.
      Keepsakes sit in the rooms: sketches kept from the table are
      pinned under it, every vault object shows its kind, the Folks
      grow by hand. "Invite a new face" (new public route
      `POST /api/builder/face/roll`, flagged per Ask-first): the
      model drafts name/role/seed through a schema-constrained
      pipeline, the engine places them with the interview's own
      deterministic rule (`_pick_tile` - reachable, unclaimed, dry),
      and keeping the editable card vaults a real `kind: "face"`
      item - the household grows, never invented. "Check the ground"
      (new public route `POST /api/builder/map/check`, deterministic
      - flagged): the draft grid is run through the real
      `maplab.validate` gate, surfaced honestly. The drawing table
      gains a fill (flood of one mark), an undo (40-step), and
      drag-to-paint. The studio listens: while visible it reads
      `/api/trace` every 10s and the Hall's fire keeps watch over
      true engine events as quiet whispers (each paired with a squeak
      when sound is on). Sound, off by default, lives in the prefs
      contract (`sound.effects/ambience/speech`, deep-merged by
      prefs.js) with one Settings row; every sound pairs with a
      visible event. The folio remembers per resident (localStorage)
      with a "forget this talk" control, and every reply can become
      a keepsake in one click ("keep this note" → vault
      `kind: "note"`) - the reply now renders live too. The Folks
      are living cards reading real `at/near/seeds` + wiki lines,
      each a door into the folio. The town sits behind glass in the
      Hall: a framed window rendering the real pack map at its real
      phase, hero lit gold, speakers lit teal, sanctuary rimmed.
      Five new tests (`tests/test_map_check.py`,
      `tests/test_face_roll.py`) cover the deterministic gate and
      the face pipeline incl. the honest no-model path; verified
      412 passed, 2 skipped. Full a11y contract held: ≥44px targets,
      luminance focus, motion off by default, plain English, sound
      paired + off.
- [x] **Container/registry: GHCR publication, .containerignore,
      compose split** (2026-09-13): VEFR images now publish to
      `ghcr.io/rylee-bee/vefr` automatically from `main` after CI
      passes. New `.github/workflows/publish-image.yml` follows the
      Worlds pattern: `workflow_run` gate on `ci` success, SHA +
      `latest` tags, OCI labels (title, description, source, license,
      revision, created), Docker Buildx, provenance disabled. New
      `.containerignore` excludes `.git`, venvs, `__pycache__`,
      `data/`, `bench/`, `experiments/`, `storyteller_packs/`,
      `.github/`, `.project/`, and env/deploy config from the build
      context. `compose.yml` restructured as portable base (pulls
      published GHCR image, `pull_policy: always`); new
      `compose.dev.yaml` for local source-tree builds
      (`podman compose -f compose.yaml -f compose.dev.yaml up --build`).
      `compose.yml` exposes `VEFR_IMAGE` env var for pinning to a
      known-good `:sha-...` tag for rollback. Health endpoint
      (`GET /api/health`) already existed; documented that it does not
      require a model — engine boots and serves UI without one.
      README updated: container quickstart references GHCR, new
      "Container images" / "Model configuration" / "Health and
      degraded state" / "Compose" sections. Public-surface guard
      updated to skip `bench/` (internal benchmark research, not
      public engine surface). Verified: `ruff check src tests scripts`
      clean; `pytest -q` 346 passed, 2 skipped; `norns validate
      --pack worlds/sample-world` ok; `check_public_surface.py` clean
      (1362 tracked files scanned).

- [x] **Public-release hardening pass** (2026-09-13,
      public-release epoch): tree sanitized of environment-specific
      references; `docs/guides/archive/` handoffs and host-specific
      `.project/` evidence deleted; `src/vefr/cli.py`'s last private
      defaults (`VEFR_DEFAULT_DEPLOY_HOST`, `VEFR_DEFAULT_BACKUP_LOCATION`)
      set to `''` with the deploy wrapper's silent-default guard
      rewritten to match; `web/packaged.html` real IP generalized;
      `--init` template host generalized to `deploy-host`. Storyteller
      WIP preserved byte-for-byte. New `scripts/check_public_surface.py`
      + `tests/test_public_surface.py` (17 tests) tripwire on
      RFC1918, homelab hostnames, private Gitea domains, the operator's
      SSH user, private paths, and obvious credential shapes. New
      GitHub Actions: `ci.yml` (ruff + blocking pytest with
      Storyteller WIP `--ignore`'d + informational WIP step +
      sample-world validate + public-surface guard), `secret-scan.yml`
      (gitleaks working-tree scan with `[allowlist]` for the test
      fixtures), `security.yml` (manual re-run). New `SECURITY.md`,
      `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/`
      (`bug_report.yml`, `feature_request.yml`), `.github/pull_request_template.md`.
      Branch protection on `main`: require PR, require `ci` +
      `secret-scan`, block force-push, block deletion, conversation
      resolution. Secret scanning + push protection + Dependabot
      alerts + Dependabot security updates enabled on the public
      repo. CodeQL default-setup enabled across actions / js / py.
      PR #2 merged at `37ef35e`. Repo flipped to public. Final gates:
      `uv run --group test ruff check src tests scripts` all checks
      passed; `python3 scripts/check_public_surface.py` clean (1345
      tracked files scanned); `uv run --group test pytest
      tests/test_public_surface.py -q` 17 passed; `uv run --group test
      norns validate --pack worlds/sample-world` ok; `uv run
      --group test pytest -q --ignore=tests/test_npc_action.py
      --ignore=tests/test_storyteller_benchmark.py` 315 passed, 0
      failed; gitleaks 230 commits scanned, no leaks found.

- [x] **License + project identity + Actions hardening** (2026-09-13,
      same public-release epoch): engine source/tooling relicensed
      from MIT to MPL-2.0 (file-level copyleft preserves improvements
      without forcing downstream applications to be MPL); worlds/
      sample-world/ (Emberfield) dedicated to the public domain under
      CC0 1.0; worlds/lore/<flavor>/ unchanged at CC BY-SA 4.0; web
      fonts retain SIL OFL 1.1 with attribution in
      `web/fonts/README.md`. New `TRADEMARKS.md` (descriptive, not a
      legal grant — "vefr" is not a registered trademark; forks
      welcome under the license, please use a distinct name for
      substantially modified versions); new `THIRD_PARTY_NOTICES.md`
      (FastAPI/Uvicorn/httpx BSD-3, Pydantic MIT, fonts SIL OFL 1.1).
      Actions hardening: third-party actions pinned to commit SHAs
      (`actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`
      = v4.2.2; `astral-sh/setup-uv@0c5e2b8115b80b4c7c5ddf6ffdd634974642d182`
      = v5.4.1) with version comment for human-readable reference.
      New `.github/CODEOWNERS` expressing "sensitive paths require
      maintainer review" (informational; branch protection enforces
      the rule). Verified gates: `uv run --group test ruff check src
      tests scripts` all checks passed; `python3
      scripts/check_public_surface.py` clean (1345 tracked files
      scanned); `uv run --group test pytest
      tests/test_public_surface.py -q` 17 passed; `uv run --group
      test pytest -q --ignore=tests/test_npc_action.py
      --ignore=tests/test_storyteller_benchmark.py` 315 passed, 0
      failed. The historical "license split: engine MIT" entry
      above remains in the ledger as the original decision;
      relicense landed via `LICENSE` file change, not by rewriting
      history.

- [x] **Truth-repair: canonical checkout documented, stale handoffs
      archived, CI added** (2026-09-07, truth-repair epoch): two
      checkouts on the dev box were documented in AGENTS.md with a
      do-not-commit-the-WIP rule for the kilo2 lane. Dated session
      snapshots (`session-handoff.md` 2026-08-31, two
      `handoff-snapshot-*` 2026-09-01 files) moved under
      `docs/guides/archive/` with a README marking them non-current;
      `deploy.md`'s reference repointed to the current `handoff.md`.
      The hard-coded pytest count in AGENTS.md was removed (it had
      drifted 200 → 307 → reality); the gate comment now says paste
      your own run's summary line and find verified counts in this
      ledger. New `.gitea/workflows/validate.yml` (first CI on this
      repo): ruff + pytest on PRs and main pushes, plus a
      pack-validation job that runs `norns validate` over every
      `worlds/*/world.json` pack. Verified: `uv run --group test
      pytest -q` → 296 passed, 2 skipped, 1 warning (0:03:35);
      `norns validate --pack worlds/sample-world` → ok. The
      machine-specific canonical-checkout path documented here was
      later corrected in the refinement pass below — the
      authoritative phrasing now lives in AGENTS.md "Active checkout
      and Storyteller WIP".
- [x] **Refinement pass: honest orientation, source-control truth,
      Trusted Translation pointer** (2026-09-12, refinement epoch):
      AGENTS.md "Canonical checkout" replaced with "Active checkout
      and Storyteller WIP" using portable language ("the checkout
      registered for VEFR in `agent-sync`") instead of the
      machine-specific path that no longer exists on the active
      checkout; the Gitea PR/tea claim corrected to GitHub
      `Rylee-Bee/vefr`; `.project/CURRENT.md` rewritten to lead with
      *phase* (refinement pass) and durable pointers, with SHA
      surfaced as `git log -1` rather than mirrored; `README.md`
      gains a concise pointer to Play-Nice's
      [Trusted Translation](https://github.com/Rylee-Bee/play-nice-contracts/blob/main/docs/principles/trusted-translation.md)
      philosophy (link, not copy); `GETTING_STARTED.md` Gitea-style
      `rylee/vefr` repo reference replaced with the public GitHub
      URL. CLI help subcommand counts (`norns` Four→Nine,
      `ratatoskr` Three→Six) are deferred — they live in
      `src/vefr/cli.py`, which is part of the protected Storyteller
      WIP; the Storyteller team should land them alongside their
      work. Play-Nice adoption pin remained
      `0cee0652fb6f13c440b1fd9cc5d78fd87cdca8ad` (no contract
      semantics changed in the new Play-Nice revision; only
      documentation did). Storyteller WIP (5 modified + 20 untracked
      files) untouched; nothing in the protected set was staged.
      Verified: `uv run --group test ruff check src tests` → All
      checks passed; `uv run --group test pytest -q
      --ignore=tests/test_npc_action.py
      --ignore=tests/test_storyteller_benchmark.py` → 298 passed
      in 266.61s; `norns validate --pack worlds/sample-world` → ok.
- [x] **Spark: a resident small brain, productionized**
      (2026-09-06, this session): the benchmark settled the model
      selection - Phi-4-mini-instruct Q4_K_M (spark-quality, 100/100
      VEFR functional score, ~1.9 GiB resident CPU-only) with
      Qwen3.5-0.8B Q8_0 (spark-tiny, 80.3/100, ~1.05 GiB) as the
      low-memory profile. `src/vefr/spark.py` builds Spark's context
      in layers from the spark contract, the loaded pack, the
      speaker's voice file, and supplied runtime state; strict
      json_schema responses validate before anything applies
      (`state_edit_check` fails closed). `ratatoskr spark
      install/status/smoke` acquires the pinned, hash-verified models,
      runs the quadlet service (loopback 8082, CPU-only, llama.cpp),
      wires VEFR_SPARK_URL, and proves the integrated path through the
      live /api/spark routes. Escalation to K2 is both a deterministic
      gate and a measured model capability (100/100). K2's
      configuration is untouched. See `docs/guides/spark.md`.

- [x] **the Figma design system integrated** (2026-09-06,
      feat/figma-theme-integration): the condensed design docs
      (design/) plus the full mockup export (design/mockups/, 36
      frames) are the reference; `web/vefr-theme.css` is the code
      home - every Figma primitive, the three semantic contrast
      themes (Warm & Easy / Bright & Clear / Nothing Hides) as
      `[data-theme]` blocks, spacing/radius/sizing scales, and the
      legacy `--bg`/`--card`/... aliases that point at them so every
      pre-existing rule themes itself. prefs.js derives `data-theme`
      from the contrast pref (one control, both vocabularies); the
      contrast option labels now carry the Figma theme names. Shell:
      the header is the 72px top bar (brand leaf, live world/act
      breadcrumbs from `/api/world`, engine StatusIndicator chip,
      zone pills) per design/HANDOFF.md; tabs/zones are ModeTab
      pills; primary actions are teal-fill `.btn-primary`; empty and
      error states got the vefr-states treatment; panel titles are
      the gold serif headers. Inter (variable woff2, SIL OFL) joined
      the self-hosted fonts for UI chrome; reading text stays on the
      prefs-driven fonts. packaged.html's inline palette realigned to
      the same primitives. Verified: ruff clean; pytest 307 passed
      with the only failures pre-existing on the base commit (a doc
      leak caught by test_pack_neutrality + untracked npc_action WIP);
      headless-browser pass at 1440/900px across all three themes,
      zones, prefs dialog, and a whisper round-trip with zero console
      errors and zero failed requests. Map: design/INTEGRATION.md.

- [x] **the engine's identity locked in** (2026-08-31, this session):
      Norse-coded + Hero's Journey as story structure + lore packs as
      data. The journey/rune anchors are in `src/vefr/journey.py`
      (whispers->Fehu, doubts->Thurisaz, feared->Kenaz, awed->Sowilo).
      Three lore packs ship: `worlds/lore/norse/` (wandering poets),
      `worlds/lore/historical-event/` (what the record couldn't hold),
      `worlds/lore/norse-runes/` (the rune-cast flavor with all 24
      Elder Futhark rune poems). Every lore pack is CC BY-SA 4.0 +
      per-pack LICENSE.md with sources. The engine reads the
      textures/names/questions; the author reads the prompt.md
      and copies it into any LLM.

- [x] **v0.1 - the skeleton**: FastAPI + ollama structured output,
      parchment UI, quadlet deploy on the deploy host
- [x] **v0.2 - the ledger**: collected whispers become the engine's
      voice anchors (Rylee curates; the cadence compounds)
- [x] **v0.3 - the forge & the vault**: items with three bonds -
      assigned (church-blue), attuned (gold, rare on purpose), cold
      (grey). Offer your hand. Kept items persist on the deploy host.
- [x] **v0.4 - the bell**: the bog at night, one ring per visit, the
      mother's chore-note in her voice - headed "For you."
- [x] **the canon**: the archive, the hero, the bell, the
      church, the dictionary, the laughing room, the labyrinth, the
      monsters, Bog & Bell style, the world's creed
- [x] **the founding myth**: the Keeper's empty throne, the Weaver's
      scorn, the Untongued - the Conserved Word vs the Fen Verse
- [x] **v1.0 - first tiles**: MAP.md became a walkable grid; the hero
      leaves the bookshop; the tower's sightlines became geometry you
      can feel
- [x] **v2.0 - the bones and the flesh**: engine/world split. All
      canon moved into the author's private story pack (logbok, ledger, map,
      voices, world.json); the engine reads everything through the
      pack loader. The town renderer is world-driven (/api/world).
      MIT on the bones; the flesh stays private. Someday: hand
      someone the bones, they grow their own story.
- [x] **the hearth**: the old soldier and the housekeeper come to the story -
      the soldier's house in the church's own shadow, one standing
      gold window, a sanctuary threshold the watch never crosses,
      plain speech and corn-bread. The the sea-folk join the canon: the
      Weaver's people, the name-keepers, seen once at the water's
      edge. And one law from the sealed layer: the game never holds
      her under.

- [x] **v1.2 - items in the world**: the vault became the game's
      inventory (carried item in the HUD); attunement on screen
      (gold ring, gold only when the world is kind); the reed
      crossing's water level became a choice (high in feared); the
      the sea-figure sighting at the water's edge (awed, gold, once).
      And the town grew 30x20 -> 40x28: the moot hall (its keeper
      keeps the roll), Katla's tavern (rumors are born there),
      Sigga's store (her ledger is not the parish ledger) - all
      with doors, verified reachable by flood-fill.
- [x] **the storytelling layer named**: style.py is saga.py -
      for the goddess who keeps stories at Sokkvabekk. Bragi
      composes the prompts; Idunn keeps the ledger that renews
      the voice.
- [x] **the rpg-js question**: answered 2026-08-30 - the custom
      renderer stays canonical. RPG-JS stays admired (MIT, a fine
      tool), and the door remains open through the pack contract:
      any future render target reads the same /api/world.
- [x] **`ratatoskr`/`norns` - the world-tree tooling**: two CLI
      entry points, story-agnostic. `ratatoskr` is the squirrel who
      ferries messages up and down Yggdrasil - skipa, test, weave
      (the file packager), and ferry (deploy / carry to NAS / fetch
      from Gitea). `norns` are the weavers - chat, validate,
      build-map, verify. `maplab.py` is the one geometry validator
      shared by both CLIs and the tests.
- [x] **the full rename, 2026-08-31**: this repo and package are
      `vefr` now (renamed several times before landing here) - the
      umbrella under which `ratatoskr` and `norns` both live as
      commands. Env vars
      (`VEFR_HOME`, `VEFR_WORLD`, `VEFR_MODEL`, `VEFR_VAULT`,
      `VEFR_KEEP_ALIVE`), and every hardcoded story reference in the
      engine (the API title, the health check's service name, the
      shared rumor system prompt, `world_name()`'s private-pack
      special-case) are gone.
      The story itself (the author's pack, `STYLE.md` included) moved
      to its own private repo, verified
      byte-identical before the move; the engine repo's history was
      then rewritten (`git filter-repo`) so no trace of it remains in
      any commit.
- [x] **the bones boot alone**: `worlds/sample-world/` (Emberfield) -
      a demonstration pack with zero story content, proven by
      physically removing the author's own pack and running the suite
      green. The engine works with any pack, or none beyond the
      sample.
- [x] **license split**: engine MIT (`src/`, `web/`, `tests/`,
      `deploy/`, `Containerfile`, `worlds/sample-world/`);
      the author's own story pack is all rights reserved, not
      covered by the engine's MIT - see that pack's own LICENSE.
- [x] **`norns chat`**: the conversational world-builder. Interviews
      canon, theme colors, phases, bonds, and one speaker's voice
      against the local ollama, starting from `worlds/sample-world/`
      so geometry can't break. The interview's flow is deterministic
      Python; the model only ever fills in prose or a hex color
      inside a schema it can't escape - `maplab.validate()` runs
      after every write. Fixed alongside it: every schema-constrained
      call in the engine (`generator`, `forge`, `bell`, `npc`, `chat`)
      now sends `"think": false` - the thinking model was dumping its
      chain-of-thought into the one string field a JSON schema left
      it, which would have shown up as narration inside rumors, item
      names, and the bell's letter.

- [x] **the session journal + story export** (2026-08-31): the
      vault was the only thing that persisted; now `journal.py` keeps
      a timestamped record of every rumor heard, line spoken, item
      kept, and the bell's letter - same atomic tmp+replace write as
      the vault, `VEFR_JOURNAL` to move it. `main.py`'s existing
      routes log after each generation, so the record is a byproduct
      of play, not a chore. `export.py` weaves the pack's title +
      logbok.md + the journal + the vault into one markdown document
      by deterministic templating (never a model call: it must work
      with ollama cold and must match what actually happened). New
      routes `GET /api/journal`, `POST /api/journal/clear`,
      `GET /api/export`; a Journal tab in `web/` reads the timeline
      back and downloads the story as a `.md`. A model-polish pass
      over the export stays available as a v2.

- [x] **shared story state** (2026-08-31): the two phase rails were
      two variables. `web/state.js` is now the one client-side state
      (a plain object, a patch function, a list of
      subscribers; no framework), and both script scopes - the town
      renderer and the tabs - read and write it. Set the world's tone
      in Rumors and the town's rail, watch radius, water level and
      canvas follow; set it in Town and the rumors rail follows.
      Keeping an item reaches the town's HUD and its gold ring without
      a tab click, because the vault list the Vault tab draws and the
      item the hero carries are the same list. `/api/world` is fetched
      once for the page instead of once per view. Two smaller things
      fell out of it: the rumors rail was hardcoded to the author's own
      four phase names (a story leak in engine HTML - any other pack's
      rumors silently fell back to its first phase), so it is built
      from the pack like the town's always was; and the Vault tab now
      loads the kept list when you open it rather than only after a
      forge. Validated by executing `state.js`, `town.js` and
      index.html's inline script under a stubbed DOM in node -
      including strict mode, to catch the undeclared-variable class of
      runtime bug that no syntax checker sees.

- [x] **inference backend: ollama -> llama.cpp on the 6900XT** (2026-08-31).
      Wall time on the live `vefr` went from ~27.6s per rumor/bell
      to ~2-5s end-to-end (curl + SSH overhead included). Root cause
      of the old slowness: the ollama container on the deploy host was the
      correct `ollama/ollama:rocm` image, but `podman inspect ollama`
      showed `Devices=[]` - no `/dev/kfd` or `/dev/dri` passed
      through, so a dense 27B Qwen was running on CPU the whole time.
      Switched to llama.cpp's OpenAI-compatible
      `/v1/chat/completions` endpoint with `gpt-oss-20b-UD-Q4_K_XL`
      (Apache-2.0, MoE 3.6B active). All five generation modules
      (`generator`, `forge`, `bell`, `npc`, `chat`) now go through
      one helper, `generator._completion(payload)`, which decides
      backend from `VEFR_LLAMACPP_URL` (preferred) or `OLLAMA_URL`
      (fallback). JSON constraint is now `response_format.json_schema`
      with `strict: true`; reasoning control is
      `chat_template_kwargs.reasoning_effort=low` (gpt-oss has no
      `off` - low/medium/high only, llama.cpp maintainers confirmed).
      The helper is monkeypatched instead
      of the wire layer, so backend swaps stay test-clean. Two btrfs-
      on-Fedora-Atomic gotchas hit along the way (documented in
      `~/llama-server/run-gptoss.sh`): podman bind sources MUST go
      through the operator's real `$HOME` and not a `/home`
      symlink (the `/home` -> `/var/home` symlink confuses
      rootless-podman statfs on the btrfs subvol);
      `HSA_OVERRIDE_GFX_VERSION=10.3.0` is required
      for the 6900XT (RDNA2/gfx1030) since llama.cpp's compiled
      runtime only recognizes gfx900/1030/1100/1200. The deploy
      quadlet was updated in place.

- [x] **the always-array world loader + the visible engine**
      (2026-08-31). `load_world()` now returns a single canonical
      shape: top-level keys (title, phases, surface, logbok,
      ledger, voices, bonds, acts) and `acts` is ALWAYS a list.
      Two on-disk shapes are supported. Flat: worlds/<name>/
      world.json + voices/ + map.md (legacy packs still work).
      Acts: worlds/<name>/world.json (pack-level contract) +
      acts/<id>/world.json (act contract) + acts/<id>/<region>/
      (map.md, voices/, sprites/). The loader walks the tree
      and discovers voices/sprites by convention. maplab.load_pack
      and maplab.write_pack round-trip both shapes; chat.py
      writes a new pack in whichever shape the scaffold uses.
      `current_act(world)` and `current_town(world)` are the
      accessors; every consumer reads through them. The canary
      pack `sample-world/` is migrated to the acts shape. The
      `surface` field is now in the always-array payload so the
      web UI can branch on it in a follow-on PR. Every loader
      step is recorded to `data/weave.jsonl` (the weave log) and
      surfaced at `/api/weave`. The Builder tab gets a "What the
      engine sees" panel that shows the resolved world and
      packages a markdown handoff bundle for an AI-buddy
      debugging session - see `docs/guides/handoff.md` for the
      format. The canary pack validates
      identically before and after the migration.

- [x] **the kilo init** (2026-08-31): `AGENTS.md` (the repo's
      operating rules - bones/flesh contract, the boundaries table,
      the gate command, the known drift) and `.kilo/kilo.jsonc`
      (project config: instructions = AGENTS.md only, uv/pytest/git
      allow-list, `data/**` + `uv.lock` edit-deny) are now tracked.
      Rylee's profile + shared agent rules load from the global
      kilo config, so this repo's instructions list stays one entry.

- [x] **the handoff guide caught up** (2026-08-31):
      `docs/guides/session-handoff.md` refreshed to the kilo-init
      HEAD + the 171-test gate; all three "honest gaps" closed out
      with evidence (real pool weave landed, mem0 live again,
      `tests/test_web_packaged.py`); the next-move table repointed
      at the surface-UI continuation.
- [x] **the LAN left the source** (2026-08-31): `VEFR_GITEA_URL`,
      `VEFR_LIVE_URL`, `VEFR_DEFAULT_DEPLOY_HOST`, and
      `VEFR_DEFAULT_BACKUP_LOCATION` (host:/path) replace the
      hardcoded Gitea IP, the live-stack IP, and the SSH host
      aliases - the engine source now carries neutral localhost
      defaults and takes its identity from the environment. The
      scaffold README derives its engine link from the checkout's
      own `origin` at runtime. Runtime data, not repo data.

- [x] **the reading row** (2026-08-31, this session): the
      Reading & sound panel, opened from a 44px trigger in the
      title bar, slides up as a bottom-sheet on mobile and a
      centered dialog on desktop. Three columns named for the
      three Norns: **Urd** (recalled settings, reset, share-link),
      **Verdandi** (live controls - text size, line spacing,
      font, contrast, colorblind-safe palette, motion, focus
      ring, density), **Skuld** (live preview of how the page
      reads right now). English labels lead; Norse names ride
      visibly as a secondary line. The full contract:
      `window.VEFR_PREFS.{get,set,preview,reset,on,shareLink,
      applyFromUrl}`; persistence is localStorage under
      `vefr-prefs`; cross-device sync is a base64-encoded URL
      (`?prefs=...`) you copy via the **Deila** button. The
      stylesheet keys off a single `<html data-prefs="...">`
      attribute set on every set/preview, so adding a new
      preference is one CSS rule and one `[data-pref-key]`
      select. The always-layer's reading row is part of the
      gate. Self-hosted Atkinson Hyperlegible Next + OpenDyslexic
      woff2 tracked under `web/fonts/` (SIL OFL); until the
      binaries are downloaded the @font-face rules 404 silently
      and the body falls through to its system serif. See
      `docs/guides/identity-terms-glossary.md` for the terms
      the panel uses.
- [x] **companion resources surveyed** (2026-08-31): a full
      CC0/MIT tool survey (engines, renderers, map authoring,
      narrative tools, art editors, audio, dev workflow) kept as a
      local research note - gitignored, since the repo may publish
      one day. Durable decisions: Kenney CC0 art ships as pack
      data once the renderer grows sprite support; Tiled (then
      LDtk) importers parked after the surface-UI work; rot.js
      algorithms get borrowed for mapgen when `norns chat` v2
      opens; frameworks skip (the custom renderer stays
      canonical); the ebook export stays a stdlib writer; idea
      credits for incompatible-but-borrowed sources live in
      README's Attribution section.

- [x] **the bones stop talking** (2026-08-31, this session):
      A1+A2+A3+A4 - the strip. Every user-visible string in the
      engine that named a specific pack's voice, place, or
      speaker (the mill / the bell / the tower / the bookshop /
      the bog / the ferryman / the roll-keeper / the wanderer / the sea-figure) is gone or
      replaced with engine-neutral prose. The engine paints
      nothing where a pack would speak - tabs show empty
      status until `/api/world` returns, the whisper button
      says `listening...` / `whispered` / `nothing came back`
      instead of `the mill turns / the mill is warm / the
      mill is silent`, the Skuld preview shows em-dashes
      where the pack's phase + speaker would live. Comment
      drift (canon names in `state.js` / `town.js` /
      `world.py` / `volumes.py` / `cli.py` / `main.py`) replaced
      with engine-neutral identifiers; the one load-bearing
      private-pack-name rename
      in `norns build-map`'s scaffold helper gets an
      explanatory comment so the history isn't lost. The
      `norns chat` builder's system prompt no longer names
      example NPCs from the author's canon. README's
      "bones and the flesh" section now carries a worked
      example: develop on vefr, write the game in
      the private story repo, ferry fetch to play. The bones
      stay empty until a pack mounts.

- [x] **the dev board** (2026-08-31, this session): the Dev zone's
      github-projects-style board - the pack's four generators
      (whispers / voices / forge / bell) as draggable cards in a
      file-tree chrome. Cards are drawn from the loaded pack
      (/api/world, shared fetch - one request per page); a column
      the pack cannot fill is seeded from a deterministic
      engine-neutral pool (Norse-coded names, no canon strings -
      the strip holds here too), so the board is never empty and
      never storyful. A fresh seed per browser persists in
      localStorage (`vefr-board-seed`), so a run is reproducible
      but never identical to the pack. Dragging a card between
      columns re-homes it and persists (`vefr-board-cards`), with
      an honest "moved" timestamp; a fresh boot loads the store
      instead of regenerating. The right rail (hidden until a card
      is selected) shows the column's real endpoint, request and
      response shapes, a "try it" button that calls the endpoint
      like the game's own buttons do (and says plainly when the
      engine does not answer), and a draft box reserved for
      `norns chat` wiring. The board boots lazily on its own tab
      - the Play path never asks for it - and `web/board.js` is
      machine-tested two ways: the vm contract harness
      (tests/fixtures/board_harness.mjs) and the full-DOM
      harness's tab tour, which now proves the board adds no
      second /api/world fetch. Packaged play files are untouched
      (the board is a served-UI Dev feature). Editing cards
      belongs to `norns chat`, not a textarea - navigation-only
      chrome on purpose.

- [x] **the shadcn layer** (2026-08-31, this session): the UI
      adopts shadcn/ui's design language as a token vocabulary +
      component anatomy - CSS custom properties only. No React, no
      Tailwind, no build step: the packaged single-file stays
      self-contained. The shadcn names (--background, --foreground,
      --card, --border, --ring, --primary, --radius...) are DERIVED
      tokens referencing the engine's own luminance-first palette,
      so the reading row's contrast/palette overrides flow through
      the entire new vocabulary unchanged - the focus ring became a
      token (--ring), replacing two long per-selector pref lists
      with one rule pair. Buttons, cards, and inputs collapsed from
      ~8 near-duplicate blocks each into one :is() anatomy (outline
      default, solid primary variant, 44px minimums, motion off);
      radii follow shadcn's scale (one base, sm/md/lg/xl derived).
      The board stylesheet rides the same tokens. The town canvas
      renderer stays custom (the rpg-js decision stands - this
      layer dresses the document UI, not the game canvas).

- [x] **the drag layer** (2026-08-31, this session): the board's
      pointer drag moved to vendored SortableJS 1.15.7 (MIT, 45KB,
      classic script, provenance in web/vendor/README.md) - native
      HTML5 DnD has no touch support, so the board was desktop-only
      before. Drops now keep their dropped position (the store syncs
      to the DOM order instead of re-rendering), the ghost/chosen
      states use the token vocabulary, and native DnD remains as the
      honest fallback when the vendor file is absent (the test
      sandbox, a packaged file without it). Keyboard users re-home
      cards without a pointer at all: the rail carries one button
      per column (current column disabled), every move announces
      through an aria-live status line. @dnd-kit/dom was evaluated
      first and rejected on evidence: v0.5.0 ships ESM-only (verified
      against the jsDelivr entrypoint), which would force an import
      map or bundler onto a no-build repo. Two real bugs caught by
      the vm harness on the way in: syncColumns originally resolved
      cards only from the target column's store array (a card
      dragged in from another column would have been silently
      dropped) and the move() rewrite had lost its render() call.

- [x] **the draft wires to the smith** (2026-08-31, this session):
      the board rail's draft box is live - it was shipped inert with
      an IOU and now keeps its promise. One thread per card, held by
      the page (the /api/builder/chat endpoint is stateless; the
      last 6 turns replay for context). Every turn carries the
      card's context - name, kind, column, current text - so the
      smith knows what the author is pointing at; the wire format
      keeps the composed message while the rail's log renders the
      short draft. The thread dies with the page: drafts are
      conversation, not lore (nothing is persisted to the pack).
      Offline, the turn comes back out of the thread and the rail
      says so plainly - the draft stays yours. The vm harness drives
      the full contract: context in the composed message, both turns
      logged, textarea cleared, honest failure leaving the thread
      empty.

- [x] **one shell, every zone** (2026-08-31, this session): the
      layout instability Rylee flagged - the page swapped between a
      narrow reading column (Play/World) and a wide workbench (Dev),
      and the World zone was a third unrelated body of bare lists -
      is gone. The shell is one width everywhere (min(80rem,
      100% - 2rem)); reading surfaces cap their own line length
      (46rem) because the short-line reading win belongs to the
      text column, not the page. The World pane now wears the same
      skeleton as the board: Characters / Relics as two columns of
      selectable cards (role=button, Enter/Space, aria-pressed,
      luminance ring) with the full record in a shared right rail.
      The pane vocabulary (board-container / board-column /
      board-cards / board-rail) is the app's shared skeleton;
      Play keeps its inline cards for now - they already show their
      whole content, and hiding it behind a selection would add
      reading load, not remove it.

- [x] **the reachable UI** (2026-08-31): header earns its title,
      9 flat tabs become 3 static zones (Play / World / Dev) with
      plain-English labels leading and Norse secondary, 44px+ targets,
      luminance-only active states, prefers-reduced-motion honored,
      keyboard focus-visible tokens, and the reading row (text size,
      line spacing, contrast, fonts) built on VEFR_PREFS.

- [x] **ratatoskr weave --pool** (2026-08-31): pre-generation pass
      during packaging inlines `window.VEFR_POOL` for offline play
      with per-combo spending tracked in localStorage and fallback to
      honest silence when spent.

- [x] **surface UI for `surface: "combat"` packs** (2026-08-31,
      `06eed41`): the web UI renders the surface. `web/index.html`
      gains the HP bar (`.hud-hp`, combat surface only), the
      phase-dependent encounter prompt (hidden in the whispers
      phase), the combat verb row posting to `/api/combat/action`
      with the response landing in the journal, and the
      `<body data-surface="...">` attribute set from the
      `/api/world` payload at load. HP is synthesized per-phase by
      `combat.hp_for_pack()`, so packs need no hp data of their
      own; plain/investigation surfaces hide the whole costume
      via CSS. Verified live on the deploy host (2026-09-01): `/api/world`
      serves `surface: combat` + `hp: {current: 4, max: 4,
      per_phase: {dusk: 3, dawn: 4}}`. The packaged half landed
      the same day (see the packaged-costume entry).

- [x] **audit 2026-09-01** (2026-09-01): 10 PR sequence resolving
      live scaffold NameError, pack contract verification (stefna_voice,
      voices dual convention, strike prompt), final story prose and
      pronoun stripping, AST shape-based neutrality guard, vefr renaming
      sweep across web globals/events, and test harness execution for
      the reading row controller.

- [x] **dev overlay & aspect inspector + engine maintenance bundle** (2026-09-01, this session):
      In-game development overlay & aspect inspector drawer with
      accessible 44px trigger, dark-mode styling, and keyboard shortcuts
      (` and F12), wired to `GET /api/builder/aspects`. Surfaces loaded pack
      aspects, active act structure, region metadata, speaker seed matrices,
      living rune cast, and recent trace events. Full DOM harness coverage
      and FastAPI route verification. Plus mechanical cleanup bundle:
      deduplicated journey attachment in `world.py` (L2), extracted shared
      `UndoBuffer` helper in `sessions.py` preserving living tree touch
      semantics across vault and journal (L3), populated speaker source on
      `NpcLine` (L4), resilient FastAPI title & static mount handling (M5),
      and robust `app_home()` fallback guards for unbundled installs (M6).

- [x] **contextual AI enhance** (2026-09-01, this session):
      Scoped structured generation calls tailored to the active screen
      and resource in authoring and dev views. Implemented `src/vefr/enhance.py`
      with strict JSON schemas for map/POI descriptions, speaker voice prompts &
      dialogue rules, and relic forge flavor/curses. Wired into FastAPI at
      `POST /api/builder/enhance/{map,voice,item}` and integrated into the
      Builder tab with accessible triggers and status reporting. Tested with
      dedicated test suite (`tests/test_enhance.py`).

- [x] **`ferry deploy` hardened as the single ship button** (2026-09-01,
      this session). `ratatoskr ferry deploy` now owns the deploy
      path end-to-end: pre-flight gate (`pytest -q` +
      `norns validate --pack sample-world`, `--skip-tests` to bypass),
      rsync the checkout, skip `podman build` when the remote image's
      `vefr.engine_sha` label already matches the local HEAD
      (`--rebuild` to force), `systemctl --user restart vefr`,
      ensure the `vefr-{template,worlds}` named volumes exist,
      post-deploy `/api/health` + `maplab verify` (`--no-health` to
      bypass). `--init` writes `deploy.toml.example` + the README
      path; the wrapper refuses to run with any silent host
      default and points operators at `--init` (a fresh clone
      without a host should explode loudly, not `ssh` a hostname
      that resolves to nothing). `Containerfile` stamps
      `ENGINE_SHA=$(git rev-parse HEAD)` as a label so the
      no-op-skip works; `VEFR_DEPLOY_IMAGE` env override. New guide
      `docs/guides/deploy.md`; cross-link in `GETTING_STARTED.md`.
      Legacy `docs/guides/deploy-rsync-dance.md` kept for old
      bind-mount hosts. Tested in `tests/test_deploy.py` (4 new
      tests, full suite 200 passed).

- [x] **deploy-day fixes, atomic with the first wrapper deploy**
      (2026-09-01, `a11e532`). Two bugs the first ferry deploy
      exposed: `norns validate --pack sample-world` accepted only
      real paths and raised `FileNotFoundError` on a bare name, so
      the pre-flight gate could never pass - `maplab.cmd_validate`
      now resolves bare names through `pack_root()` the way
      `handbok`/`doctor`/`export` already did (3 tests in
      `tests/test_validate_pack_path.py`). And the post-deploy
      health probe hit `127.0.0.1` on the dev box (its SSH alias
      resolved to the wrong host) and gave up after one
      fixed 2-second sleep - it now probes through an SSH
      port-forward with a 20-attempt x 1.5s retry loop.

- [x] **dev zone polish: board, draft thread, inspector filter**
      (2026-09-01, PR #32, `526e06c`). Board drags within a column
      now announce `reordered in <col>.` in the board-status
      aria-live region (cross-column moves already did; intra-column
      was silent), and cards get a grabbing cursor while held. The
      draft-to-the-smith thread renders as labeled paragraphs
      (`board-chat-user` / `board-chat-smith`, luminance carries the
      role) instead of one flat text blob, auto-scrolls to the
      newest turn, gains a Clear thread button, and says under the
      log that the last 6 turns replay - the 7-turn harness run
      proves the cap. The aspect inspector gains a section filter
      (`dev-drawer-filter` + aria-live match count) that re-renders
      from the stored `/api/builder/aspects` payload - no refetch
      per keystroke; an empty query restores all six sections, and a
      no-match query says `no sections match.` plainly. Two real
      bugs the harnesses caught before any human did: the smith
      paragraph was classed `board-chat-assistant` (the CSS and the
      claim say smith), and the filter read `.html` off a string.
      Live on the deploy host after deploy (`526e06c`): served index.html
      carries the new ids, served board.css carries the grabbing
      cursor. Discovered and fixed along the way: the dev-box
      SSH alias resolves correctly and matches `VEFR_DEPLOY_HOST`,
      so a bare IP literal is not needed.

- [x] **reading row: Urd/Verdandi/Skuld live readbacks** (2026-09-01,
      PR #33, `a579d90`). The Skuld empty-state honesty check the
      matrix called for: the sample text was already engine-neutral
      (passes - no sample-world voice, the em-dash rule holds), but
      its meta line was dead placeholders - `phase: - speaker: -` for
      data the panel never had. Urd now carries a saved-state readout
      and Skuld a live `reading now:` readback, both fed by the same
      VEFR_PREFS values on every change, aria-live, layout pinned by
      min-height. The fake phase/speaker line is gone. Sound
      controls deliberately absent - no sound engine exists; sliders
      for silence would be dishonest UI. Harness checks cover change
      + reset on both readouts. Live on the deploy host after deploy
      (`a579d90`).

- [x] **api manner: honest 422/404s + the route guide tells the
      truth** (2026-09-01, PR #34, `2bfa064`). Found by driving the
      play loop live: `POST /api/vault` took a bare dict and answered
      a caller's typo (a missing `kind`) with a bare 500 - it now
      takes a typed `ItemCard` and answers 422 naming the missing
      fields. `POST /api/npc` answered an unknown speaker with a
      RuntimeError 500, and a voice-less pack would have died inside
      `next(iter({}))` - both are 404s in the engine's own words now
      (unreachable by the UI on sample-world; hand-rolled callers
      get the honesty too). And `one-source-of-routes.md` - the
      anti-drift doc itself - was drifted: it claimed a
      `POST /api/starred` that does not exist and listed 14 routes
      where 41 are served (missing `/api/world` itself, `/api/handoff`,
      the enhance trio, aspects, the journal/vault index routes).
      Regenerated from `app.routes`, dated. 4 new tests
      (`tests/test_api_manner.py`), suite 207 passed. Live-verified
      on the deploy host after deploy.

- [x] **block 5: sample-world polish - the pack stays neutral about
      bonds** (2026-09-01, PR #35, `041b77d`). Playing the pack live
      surfaced one defect: the board's forge response doc hardcoded
      `assigned | attuned | cold` - a bond list sample-world has
      never heard of (it draws given/found/cold). The doc now says
      `<the pack's bond keys>` with the reason in a comment, and
      `test_board_wired_into_chrome` refuses any hardcoded bond list
      in board.js (the canon-strings rule, applied to pack
      vocabulary). The pack itself validated and played green - and
      a handoff myth died on the record: `voices: 0` counts voice
      files, not speakers; sample-world ships one speaker (The
      Keeper) and the default-speaker npc flow works live.

- [x] **the packaged file wears the combat costume** (2026-09-01,
      PR #36, `bb4a665`). The web-UI half of the surface work landed
      in `06eed41`; this closes the packaged half. The weave
      artifact's template now carries the HP bar, the encounter
      prompt, and the verb row - data-surface comes from the pack at
      play time (a plain pack never sees the costume), HP is the
      same positional per-phase scale as combat.py inlined, the
      prompt text never names a pack's phase vocabulary, and the
      verbs record to a local localStorage journal - the same
      no-failure contract as /api/combat/action, minus the server.
      Test: builds a real packaged file through cmd_build_web and
      asserts the costume shipped, with a phase-name neutrality
      guard.

- [x] **chat v2: the interview grows the map and the town's
      people** (2026-09-01, PR #37, `59b3a25`). The interview is no
      longer frozen at the scaffold's proven-valid layout. The map:
      the model proposes run-length rows (build_map's own format) at
      the scaffold's exact dimensions using only the scaffold's
      legend characters; a proposal never touches the pack until
      maplab.validate() passes on a deep copy - two tries, then the
      proven layout stays and the author is told so. The gate is
      geometry-only; the interview's final validate is the full
      gate. Speakers: the town takes 1-3 voices (blank = 1) - extra
      voices get drafted seeds and a voice file, but their tile is
      deterministic code (reachable, unoccupied, unflooded,
      widest-spread band); no tile, no speaker, said plainly. The
      model call sits in chat.py's propose_map/_add_speaker;
      deterministic surfaces stay deterministic. 7 new tests, suite
      215 passed. Both changes live on the deploy host after deploy.

- [x] **the dev box plays** (2026-09-01, this session): five
      playability gaps closed as one bundle. (a) The model endpoint
      is a variable, never a host: `example.env` (tracked, neutral
      placeholders) copies to a gitignored `.env`, sourced before
      any entry point - GETTING_STARTED shows the shape. (b) The
      reading row's fonts ship: Atkinson Hyperlegible Next +
      OpenDyslexic woff2 (latin 400/700, vendored from Fontsource,
      SIL OFL) now tracked under `web/fonts/` with provenance - the
      font and contrast choices stop 404ing and the packaged file
      carries them from the first byte. (c) The road walked: journal
      kind `move`, `POST /api/journal/move` (42 routes), `town.js`
      posts one arrival per change of place (never per tile), the
      packaged file keeps the same journal in localStorage, and the
      export's "The Fen Walked" section witnesses the journey - the
      export.py TODO from earlier sessions closed. (d) The pool
      re-weaves: when the woven pool is spent, a small seeded
      composer re-splices its cloth - every word is real model
      output, whispers may cross combos (a rumor travels), npc lines
      stay locked to their speaker's own words, the status line says
      `woven anew from the pool's cloth.`, and with no pool at all
      the honest silence holds. Deterministic per save (mulberry32
      over a localStorage save-seed). The no-pool generator (pack-
      supplied whisper fragments) stays on Next - it is a pack-
      contract question. (e) The 76 runtime-state files under `data/`
      plus `worlds/poolworld/world-tree.md` left the index (`git rm
      -r --cached`); the gitignore rules hold alone and AGENTS.md's
      known-drift note reads none. Gate: 221 passed, 2 skipped
      (`uv run --group test pytest -q`), ruff clean.

- [x] **the no-pool world speaks** (2026-09-01, this session): the
      offline/no-server fallback's remaining half. Convention:
      `voices/<name>.fragments.md` beside a voice file carries that
      speaker's speakable lines - bullet lines speak, every other
      line is an author note. The loader strips the `.fragments`
      suffix, never registers a fragments file as a voice (the stem
      trap is test-pinned), and merges banks across act regions in
      file order - a region's bank travels with its own speakers.
      The packaged composer's ladder is now: live model -> woven
      pool -> the pool's own cloth -> the pack's own fragments ->
      honest silence, with the status line naming the rung (`from
      the pack's own fragments.` / `from their own fragments.`). An
      npc line only ever splices its own speaker's bank; fewer than
      two lines stays silent. sample-world ships the canary
      (`voices/keeper.fragments.md`), the package inlines the banks
      (`window.VEFR_FRAGMENTS`), and the pack-contract docstring
      documents the convention. `norns chat` v2 can later interview
      banks out of the author the way it drafts voice files. Gate:
      225 passed, 2 skipped (`uv run --group test pytest -q`), ruff
      clean.

- [x] **the ledger forgets no name** (2026-09-01, this session):
      the neutrality work's final three landed changes, recorded
      together. The tree scrub (PR #40): every tracked trace of the
      private pack and game names gone from tests, docs, LICENSE,
      and the guides - the two previously-skipped fixture suites
      now run against the tracked canary instead of skipping - and
      the two flagged follow-ups closed with it (`/api/builder/
      resolved` surfaces the fragment banks; the surface-UI entry
      no longer claims a half that the packaged-costume PR closed).
      The canon-name sweep (PR #41): the private-term list's
      character names swept from the synthetic fixtures and the
      ROADMAP story descriptions; the lore packs stay by design.
      The history scrub: a third filter-repo pass (backed up and
      verified, per the AGENTS.md boundary) rewrote every blob,
      commit message, and historical path name-free across all 200
      commits. The anti-regression guard's scope now covers src/,
      web/, tests/, docs/, and the root documents - it caught two
      stragglers on its first run. Gate: 240 passed, 0 skipped
      (`uv run --group test pytest -q`), ruff clean.

- [x] **the deploy button** (2026-09-01, this session):
      deploy.toml scaffolding landed (`--init` writes it; the
      per-host twin is gitignored like `.env`; the dev box's copy
      points at the deploy host and `.env` carries `VEFR_DEPLOY_HOST`) -
      and the deploy it drove surfaced a real wrinkle: the live
      quadlet's rw bind (`~/vefr-worlds/`) shadowed the engine's
      own sample-world with a pre-acts stale copy, so rebuilt
      templates never reached the running pack. The stale copy
      moved to `~/vefr-worlds-backup-20260901/` (starred-whispers
      preserved); engine-shipped packs now serve from the ro
      template and refresh on every image build, while author
      packs still land in the rw bind via ferry fetch. Verified
      live: health 200, the resolved view shows the keeper bank
      (6 lines), fonts 200.

- [x] **the wrapper reads its own config** (2026-09-01, this
      session): three wrapper additions for the recurring frictions
      the deploy-day work surfaced. `ferry deploy` consumes
      `deploy.toml` directly (stdlib tomllib; host and image
      resolve from it whenever --flags and env are silent - the
      export dance is gone, and a malformed toml reads as absent
      rather than taking the deploy path down). `skipa` grew two
      checks inside its existing seven questions: Q3 now runs the
      shadow check on the deploy host's rw bind and names any
      engine-shipped pack that would hide a freshly built template
      (the deploy-day find), and Q2 reports the reading-row fonts
      (0/4 would mean the woff2s never landed). `norns doctor`
      falls back to deploy.toml's url for the live check when
      `VEFR_LIVE_URL` is unset. And the deploy tunnel no longer
      leaks: `ssh -fN` forked past the Popen pid so `terminate()`
      could never reach it - one orphaned tunnel per deploy (three
      on the dev box as of today, killed; `-N` keeps the process
      where the finally can reach it). GETTING_STARTED's deploy
      section drops the export line. Gate: 247 passed
      (`uv run --group test pytest -q`), ruff clean.

- [x] **the Play workspace can be composed OR free-docked** (2026-09-03):
      the workspace is one responsive shell from 0 to 1179px (context left,
      game centre, journal right on wide screens; Town spans the width
      on medium; one panel at a time on narrow), and turns into a free
      dock of five windows (Town / Whispers / Bell / Vault / Journal)
      at >=1180px, matching the ChatGPT free-dock concept. Plain-English
      panel names with Norse `.sub` tags in the title bars (matches the
      existing tab-button convention), 44px drag/resize affordances,
      luminance-only focus, `prefers-reduced-motion` zeroes every
      transition, pointer drag throttled via rAF, localStorage
      persistence under `vefr:dock:v1` (versioned + merge-back-from-
      defaults on load). Keyboard parity: Enter/Space to grab, Arrow
      keys to move, Escape to cancel. "Reset dock layout" lives in the
      dev drawer so the player never sees it. Medium and narrow screens
      keep the composed shape (the inclusive-forward rule that says
      narrow gets a stable layout). Two commits:
      `wip: compose the play workspace` and
      `feat: free-dock Play workspace`. Gate: 248 passed
      (`uv run --group test pytest -q`), ruff clean; 30+ new checks
      in `tests/fixtures/dom_harness.mjs`.

- [x] **free-dock review fix-ups** (2026-09-03, this session): the
      landing had two reviewable defects caught in a headless-Chrome
      verification pass against the running engine. First: the
      `@media (min-width: var(--free-dock-breakpoint))` block is invalid
      CSS - browsers drop the whole rule when a `var()` appears in a
      media-query condition, so the entire free-dock structural
      enablement (window frames, drag handles, absolute positioning)
      silently never applied. Fix: literal `1180px` in the media query;
      the `--free-dock-breakpoint` custom property is kept on `:root`
      for JS-side reads via `getComputedStyle`, and the comment header
      on both declarations names the literal as the single source of
      truth. Second: the `density=compact` pref was setting
      `min-height: 36px` on tabs / zone buttons / phase-rail buttons,
      which violates the Always-target >= 44px rule (AGENTS.md).
      Fix: drop only `min-height`, keep the `padding: 0.35rem 0.7rem`
      trim (compact visually, contract intact). Adds
      `.gitattributes` stamping `text eol=lf` on `web/*.html`,
      `web/*.js`, `web/*.css`, `tests/**/*.mjs`, `tests/**/*.py`,
      `src/**/*.py`, `*.md` so Windows-checkout CRLF churn stops
      polluting future diffs - the actual normalization of existing
      mixed-ending files is deferred to a separate maintenance PR
      (mixing a 7000-line line-ending rewrite with a 20-line
      functional UI fix is exactly the diff-hygiene failure this
      guardrail exists to prevent). New regression file
      `tests/test_web_css_structure.py` (3 tests) catches: any
      `@media` condition using `var()`; drift between the CSS
      `--free-dock-breakpoint` value, the `@media` literal, and the
      JS `FREE_BREAKPOINT` fallback (all must stay 1180); any compact-
      density min-height below 44px. Browser-verified at 1280x800
      (free-dock frames visible, all five panels with DRAG/snap/min
      controls), 1100x900 (composed two-column, no free-dock leak),
      760x900 (composed still engaged at the breakpoint edge),
      700x900 (single active panel, no horizontal scroll, dock state
      from earlier wide-viewport usage doesn't break narrow layout).
      Live engine on the deploy host (`deploy-host:8820`) independently
      reproduced the pre-fix defect at 1280px. Gate: 251 passed
      (`uv run --group test pytest -q`), ruff clean.

- [x] **Storyteller Pack provider seam + audition harness** (2026-09-04,
      this session): the engine is now model-neutral. `Provider` enum
      is two values (OLLAMA + OPENAI_COMPATIBLE; llama.cpp / LM Studio /
      vLLM / LocalAI / TGI all hang off the latter as tested runtimes).
      The Tier ladder (0 minimum → 1 small → 2 creative → 3 smart
      control → 4 BYOM) is encoded in `[capabilities]` flags. New
      `src/vefr/storyteller.py` resolves the active storyteller from
      `VEFR_STORYTELLER` env, the `data/storytellers/active.toml`
      marker, installed packs, bundled packs, or the engine reference
      (gpt-oss-20b, kept for back-compat so existing tests still pass).
      Five audition packs ship under `storyteller_packs/`
      (gpt-oss-20b-reference, gryphe-style-gemma-12b creative ref,
      gemma4-e2b / gemma4-e4b / ministral3-3b); Qwen2.5-3B-Instruct
      sits under `data/storytellers/` as an evaluation-only candidate
      (research-only license, never a shippable default). `ScenePacket`
      + `norns storyteller-test --model/--matrix/--scene/--runs/--seed
      /--blind` give Rylei a side-by-side audition harness with
      artifacts saved to `artifacts/storyteller-tests/<ts>/{manifest.json,
      <pack>.txt, blind_map.txt}`. Missing models SKIP cleanly, no
      benchmark scores, no automatic judges. `/data/storytellers/`
      gitignored per the existing runtime-state convention. Gate: 278
      passed (`uv run --group test pytest -q`), ruff clean; the
      pack-neutrality test caught a private-story leak in a docstring
      and was fixed before merge.

- [x] **storyteller capability benchmark (blind A/B/C/D)** (2026-09-04,
      this session): the second-tier audition harness. Nine new
      fixtures (`hidden-fact-trap`, `immediate-interruption`,
      `old-promise`, `player-accusation`, `mythic-stranger`,
      `neutral-quiet-scene`, `gameplay-help`, `ambiguous-clue`,
      `player-surprising-action`) join the existing Rosa anchor for
      ten total. Each tests one or two specific capabilities; each
      carries an optional `forbidden_strings` list for deterministic
      hard-fail detection. New `src/vefr/storyteller_benchmark.py`
      assigns stable A/B/C/D labels (seeded, shuffled so position
      reveals nothing), runs every fixture against every configured
      pack N times, and writes a per-fixture blind review file plus
      a private `identity.json` mapping. `norns
      storyteller-benchmark {run,reveal,review}` exposes the three
      modes. Reveal step merges identity with hard-fail counts and
      pack metadata (license, quantization) so the reviewer can read
      prose, write A/B/C/D rankings, then compare against model cost.
      No automatic winner, no benchmark score, no LLM judge. Gate:
      293 passed (`uv run --group test pytest -q`), ruff clean; the
      pack-neutrality gate caught a gendered pronoun in a docstring
      and was fixed before claim. (A pre-existing doc leak in
      `docs/guides/accessibility-contract.md` flagged for separate
      review.)

## Next
- (2026-09-16) `feat/dev-board` (123-commit orphan branch, dev-board UI
      chrome: repo header, file-tree, 4-col grid, drag-rank, right-rail
      stub) is **preserved on origin, unmerged** — assessment pending,
      do not discard without a bundle backup.
- [ ] **interactive chat helper**: inline conversational assistant in
      the builder UI answering world-building questions and adjusting pack data.
      Acceptance: persistent 6-turn chat in Builder tab successfully calls
      `/api/builder/chat` with pack context.
      (Existing machinery: `chat.py`, `/api/builder/chat`).
- [ ] **formatted ebook export**: single-document narrative exporter
      formatting playthroughs with chapter headings, character wiki, and
      collected relics. Acceptance: `/api/export` generates clean e-reader
      compatible EPUB/Markdown artifact with full metadata.
      (Existing machinery: `export.py`, deterministic preface templating).
- [ ] **engine + world full git scaffold**: standalone repository exporter
      packaging engine bones and author pack into an independent git project.
      Acceptance: `ratatoskr ferry scaffold --full` creates functional standalone
      repo with passing offline test suite.
      (Existing machinery: `cmd_scaffold`, pack contract loader).
- [ ] **Tiled map importer** (parked after the surface-UI work):
      `norns import-tiled map.json --pack X` reads Tiled's JSON
      export - visual map authoring, the storyteller-critical gap -
      and writes `map.md` + contract points through
      `maplab.build_map` + `maplab.validate()`. Thin and optional;
      text authoring stays canonical, no Tiled dependency. Tiled
      1.10's JS scripting API could later host a one-click "export
      as vefr pack" from inside the editor. See
      `docs/guides/companion-resources.md`.
- [ ] **more lore packs**: worlds/lore/<new-flavor>/ directories.
      Adding one is data-only (mkdir + four markdown files); the
      engine discovers it. Future flavors: homeric, east-asian-
      folklore, jewish-diaspora, contemporary-urban. Each one is
      a literary mood-board for fiction, licensed CC BY-SA 4.0.
- [ ] **the marketplace**: a community place to share, search, and
      rate engine add-ons - world packs, lore packs, sprites, map
      recipes, and model settings ("local LLM packs": someone's
      perfect llama.cpp + gpt-oss configuration for their exact
      hardware, shareable as data). The distribution path already
      exists (`ferry fetch --pull`, the Builder tab's import by
      owner/name), so v1 is an index over plain git repos, not new
      infrastructure - ratings live with the community, and
      discovery may grow a `norns market` command. The always-
      layer's "private until it isn't" made social.
- [ ] **accessible controls and audio-pairing**: the keybinds remap
      (GAG Basic, localStorage config) and audio-pairing hooks for
      visual event pairing when sound effects land.

## The always-layer

- the loop: whisper -> keep what's true -> the ledger -> the voice
  compounds
- the backups: Gitea, the durable clone, the NAS bundle
- inclusive-forward: every screen answers for different needs -
  reading load, target size, contrast over color, motion off by
  default, and when sound arrives, every sound paired with a
  visual event. It is part of the gate, not a follow-up.
- private until it isn't: one checkbox, whenever - or never. Both
  are complete endings.
