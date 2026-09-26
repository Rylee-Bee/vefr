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
