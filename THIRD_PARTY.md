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
| Kenney asset packs | CC0 | `worlds/sample-world/` sprites | the teaching canvas |

Model weights carry their own licenses (Qwen3, bge-m3, SmolVLM2 families);
see `docs/guides/bundled-brain.md` for the fleet and its sources.
