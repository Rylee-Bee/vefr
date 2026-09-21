# Third-Party Notices

VEFR depends on, vendors, or links to the following third-party
material. Each entry preserves the upstream license and attribution
the upstream project requires.

## Runtime dependencies

| Package | License | Source |
|---|---|---|
| FastAPI | BSD-3-Clause | https://github.com/tiangolo/fastapi |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| httpx | BSD-3-Clause | https://github.com/encode/httpx |
| Pydantic | MIT | https://github.com/pydantic/pydantic |

These are listed in `pyproject.toml` and resolved at install time
via `uv`. The licenses above are the upstream project licenses;
neither FastAPI, Uvicorn, httpx, nor Pydantic grant any additional
rights to this project.

## Bundled web fonts

All font files under `web/fonts/` are licensed under the
[SIL Open Font License 1.1](https://openfontlicense.org/). Each
file retains its upstream license and attribution in
`web/fonts/README.md`.

| Family | License | Upstream |
|---|---|---|
| Inter | SIL OFL 1.1 | https://rsms.me/inter/ |
| Atkinson Hyperlegible Next | SIL OFL 1.1 | https://www.brailleinstitute.org/freefont/ |
| OpenDyslexic | SIL OFL 1.1 | https://opendyslexic.org/ |

The SIL OFL 1.1 permits redistribution of the font files themselves
with the license notice; it does not impose copyleft on code that
references them.

## World packs

- `worlds/sample-world/` (Emberfield) — the *world text* (map, voices,
  lore, contracts) is dedicated to the public domain under CC0 1.0; see
  `worlds/sample-world/LICENSE`.
- `worlds/sample-world/assets/kenney/` — bundled room/prop tiles from
  Kenney (kenney.nl), licensed CC0 1.0 (public domain, no attribution
  required); see that folder's `LICENSE-*.txt`. Optional — the demo's
  town map renders in code and does not require them.
- `worlds/lore/<flavor>/` — Creative Commons Attribution-ShareAlike
  4.0 International (CC BY-SA 4.0); see each pack's `LICENSE.md`.

## Generated artifacts and runtime state

- `data/` is gitignored and never shipped.
- `artifacts/` is gitignored and never shipped.
- Storyteller WIP packs under `storyteller_packs/` (untracked) and
  fixtures under `tests/fixtures/storyteller/` (untracked) are
  protected WIP and are not part of this repository.
