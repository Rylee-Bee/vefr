# Split `web/packaged.html` into blocks (built 2026-10-04: slices 1-4 in one mechanical step; Rylee chose "refactor first")

**Built.** The player is 56 parts in `web/player/parts/` (head, style, shell, the pure engines, the town closure in its own sections, the skin, the title screen), listed in `web/player/manifest.json`, joined byte for byte by `scripts/build_player.py` into the committed `web/packaged.html`. Proof: `scripts/weave_digest.py` printed identical SHA-256s for every pack before and after (cottage-of-the-breeze `dfb0ee9f...`, sample-world `419b5a03...`); `tests/test_player_build.py` (6 cases, written first) keeps the generated file honest in CI. The slices below were done as one mechanical cut because a text-level split cannot change behaviour. What stays for later: splitting the 905-line `town-input-and-turns` and 564-line `the-camera` parts further, and giving parts real module boundaries.


## Why
`web/packaged.html` is one 6,600-line file: markup, CSS, the pure engines (rules, growth, equipment, album, sound, locks) and the wiring. Every feature added in the Cottage night grew it (album, sound, walk sheets, end card). Edits collide, foremen get lost in it, and 26 files (tests, the weaver, packaging) read it directly.

## Design: split the source, keep the generated file
- New source tree `web/player/`: `shell.html` (the markup and `{{placeholders}}`), `style.css`, one file per pure block (`rules.js`, `growth.js`, `equip.js`, `album.js`, `sound.js`, ...) and `wiring.js` (the player). A tiny build step (`scripts/build_player.py`) concatenates them in a fixed order into **`web/packaged.html`, which stays committed**, like Blueprint's generated output.
- Because `web/packaged.html` keeps its path and shape, the 26 consumers, the wheel's package data, the Containerfile and the deploy are untouched. A check (`scripts/build_player.py --check`, wired into `vefr doctor` and CI) fails if the generated file is stale, so nobody edits it by hand.
- The existing `// -- name start --` / `// -- name end --` markers become the block boundaries.

## Proof it changed nothing
`scripts/weave_digest.py` (added with this plan) prints a SHA-256 of the woven player for each shipped pack. Run it before and after: the lines must match byte for byte. The full suite (1682 tests) and the Cottage bot (`cottage-of-the-breeze/tests/playthrough`, desktop and phone, plus `axe_panels.py`) must pass unchanged.

## Slices (each its own PR, tests first where there is behaviour; foreman-built, diff read by hand)
1. `scripts/build_player.py` + `--check` + the digest proof, with a no-op split (one file in, one file out).
2. Move CSS and the markup shell out.
3. Move each pure block out (rules, growth, equip, album, sound), one PR each.
4. Move the wiring last; delete nothing.

## Risks
- Packaging: the wheel and container include `web/packaged.html` only; confirm the new `web/player/` is not needed at runtime (it is not: the generated file is). Verify with `vefr doctor` and a container build (Containerfile is unverified, Cottage #66 is the same concern).
- Merge conflicts with in-flight work: do it when no other foreman touches the file.

## Not in scope
Behaviour changes, new features, renaming anything. Act advance (ADR 0006) and status effects (fire first, Rylee 2026-10-04) come after this.
