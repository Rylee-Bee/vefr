# web/fonts/

Self-hosted fonts: the UI font for the Figma-derived design system
(`Inter-Variable.woff2`) plus the reading fonts for the Reading &
sound preferences panel. All woff2 files below are tracked in git
(SIL OFL 1.1 permits redistribution with the license notice; see each
family's license link) so a fresh clone and the `ratatoskr weave`
packaged file both work offline from the first byte.

## Inter (UI font)

- Source: https://rsms.me/inter/ (served via Google Fonts v20)
- License: SIL Open Font License 1.1
- Web file needed: `Inter-Variable.woff2` (one variable file,
  weights 100-900)
- Vendored: 2026-09-06, latin subset, from the `Inter` Google Fonts
  CSS2 endpoint with a browser UA (single variable woff2).
- Used by: `web/vefr-theme.css` (`--font-ui`). The design system
  (design/HANDOFF.md, Typography) names Inter as the one UI family.
  Body/reading text stays on the prefs-driven reading font below.

## Cinzel (engraved display face)

- Source: https://github.com/NDISCOVER/Cinzel (Natanael Gama)
- License: SIL Open Font License 1.1
- Web file needed: `Cinzel-Variable.woff2` (one variable file,
  weights 400-900)
- Vendored: 2026-09-25, latin subset, from the `Cinzel` Google Fonts
  CSS2 endpoint with a browser UA (single variable woff2).
- Used by: `web/studio.css` (`--studio-engraved`): the top bar,
  room headers, headings and buttons. Display only; body text stays
  on the UI and reading fonts.

## Noto Sans Runic (rune staves)

- Source: https://fonts.google.com/noto/specimen/Noto+Sans+Runic
- License: SIL Open Font License 1.1
- Web file needed: `NotoSansRunic-Regular.woff2`
- Vendored: 2026-09-25 from the Google Fonts CSS2 endpoint with a browser
  UA. Most systems ship no Runic font, so without it the Casting Table's
  staves render as empty boxes.
- Used by: `web/studio.css` (`.rune-stone__stave`).

## Atkinson Hyperlegible Next

- Source: https://www.brailleinstitute.org/freefont/
- License: SIL Open Font License 1.1 (free for personal and
  commercial use)
- Web files needed: `AtkinsonHyperlegibleNext-Regular.woff2`,
  `AtkinsonHyperlegibleNext-Bold.woff2`
- Vendored from: Fontsource (`@fontsource/atkinson-hyperlegible-next`,
  latin subset, 400/700 normal) via cdn.jsdelivr.net, 2026-09-01.

## OpenDyslexic

- Source: https://opendyslexic.org/ (downloads via Itch.io)
- License: SIL Open Font License 1.1
- Web files needed: `OpenDyslexic-Regular.woff2`,
  `OpenDyslexic-Bold.woff2`
- Vendored from: Fontsource (`@fontsource/opendyslexic`, latin
  subset, 400/700 normal) via cdn.jsdelivr.net, 2026-09-01.
- Declared for the workshop in `web/studio.css` (2026-09-25; before
  that the workshop never loaded it and fell back to Georgia).

## Crimson Pro (the reading face a skin may choose)

- Upstream project: The Crimson Pro Project Authors,
  https://github.com/Fonthausen/CrimsonPro. That is the name written
  into the font itself (name ID 0: "Copyright 2018 The Crimson Pro
  Project Authors (https://github.com/Fonthausen/CrimsonPro)") and
  into the license beside it.
- Vendored from: Fontsource, npm `@fontsource-variable/crimson-pro`
  version 5.3.0, file `files/crimson-pro-latin-wght-normal.woff2`,
  2026-10-04. That file is byte-for-byte the one in this folder:
  sha256 `20ce4189b9e41b3439a2a36dd63deff44b6d91182532202cb96b65521b4a3c23`
  (48200 bytes). To re-vendor: `npm pack @fontsource-variable/crimson-pro@5.3.0`
  and copy that one file.
- License: SIL Open Font License 1.1, which is what Fontsource's
  metadata declares (`OFL-1.1`) and what the bundled OFL text is.
  Kept beside the file as `CrimsonPro-OFL.txt`: Fontsource's `LICENSE`
  for the package, with its duplicated Italic copyright line removed.
  The binary's name ID 14 also points at the license
  (https://scripts.sil.org/OFL).
- Web file needed: `CrimsonPro-Variable.woff2` (one variable file,
  weights 200-900)
- Family version in the file: 1.003, "Crimson Pro Regular"
  (name IDs 5 and 6), 1000 upem, one `wght` axis 200-900.
- Vendored: 2026-10-04.
- Used by: the woven player (`src/vefr/cli.py`, `_PLAYER_FONTS`), so a
  skin can name it and the type is there offline. Cinzel, Atkinson
  Hyperlegible Next and Crimson Pro are the whole menu a skin may
  choose from: `SKIN_FONTS` in `src/vefr/maplab.py` is the list the
  validator checks against.

## Install

The exact filenames above are what `web/index.html`'s
`@font-face` rules reference; they are tracked, so nothing to do.
To refresh a family, re-download the woff2 at the same filenames
and keep the OFL license note with it.

If the files are missing, the CSS `@font-face` rules 404
silently and the panel falls back to the engine's system serif
(`Georgia, 'Times New Roman', serif`). The layout and the
data-prefs hook still work without the woff2s - only the
literal glyphs change.

## Why self-host

Two reasons, both in the always-layer:

1. **Offline-first.** The `ratatoskr weave` packaged file ships
   the engine and the world as a single HTML file. If a font is
   on a CDN, it can't load.
2. **Private until it isn't.** No third-party requests leave the
   browser. The story doesn't ping anyone when you play it.
