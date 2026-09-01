# web/fonts/

Self-hosted reading fonts for the Reading & sound preferences
panel. Tracked-empty directory: the woff2 binaries ship under
this path but are NOT included in git because they're
third-party downloads. Add them with the script below.

## Atkinson Hyperlegible Next

- Source: https://www.brailleinstitute.org/freefont/
- License: SIL Open Font License 1.1 (free for personal and
  commercial use)
- Web files needed: `AtkinsonHyperlegibleNext-Regular.woff2`,
  `AtkinsonHyperlegibleNext-Bold.woff2`

## OpenDyslexic

- Source: https://opendyslexic.org/ (downloads via Itch.io)
- License: SIL Open Font License 1.1
- Web files needed: `OpenDyslexic-Regular.woff2`,
  `OpenDyslexic-Bold.woff2`

## Install

Download the latest woff2 files for both families and drop them
in this directory. The exact filenames above are what
`web/index.html`'s `@font-face` rules reference, so as long as
those four files land here the panel works.

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
