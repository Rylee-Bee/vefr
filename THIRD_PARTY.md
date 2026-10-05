# Third-party notices

The engine runtime itself depends only on fastapi, uvicorn, httpx, and
pydantic (see pyproject.toml). Everything below is vendored or dev-only
tooling; none of it ships in the woven single-file player or runs at
runtime.

| Component | License | Where | Why |
|---|---|---|---|
| axe-core 4.13.0 (vendored `axe.min.js`) | MPL-2.0 | `scripts/vendor/axe.min.js` (+ `.LICENSE`) | the accessibility gate (`scripts/a11y_check.py`); same license family as this engine |
| jsdom | MIT | `package.json` devDependency | real-DOM execution for `tests/fixtures/kitchen_harness.mjs` (the pleasant-loop harness) |
| actionlint 1.7.12 | MIT | downloaded + checksum-verified in CI only | workflow lint (`.github/workflows/dev-guards.yml`) |
| zizmor 1.30.1 | MIT | `uv tool run` in CI only | workflow security lint |
| Playwright | Apache-2.0 | test dependency group | screenshots, a11y gate, visual regression |

Model weights carry their own licenses (Qwen3, bge-m3, SmolVLM2 families);
see `docs/guides/bundled-brain.md` for the fleet and its sources.

The web fonts under `web/fonts/` are a different kind of vendored: they DO
ship, inlined into the woven single-file player so a game needs no network
for its type. Cinzel, Atkinson Hyperlegible Next and Crimson Pro (added
2026-10-04) are the three families a skin may name. All are SIL OFL 1.1;
the table and the license files are in `THIRD_PARTY_NOTICES.md`.
