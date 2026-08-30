# Old Name - Style Guide

> The art direction of the archive. The world is quiet, dusky,
> held-breath - and the game must be a place Rylee's eyes can live in
> for hours. The accessibility constraint is not a compromise on the
> art. It IS the art direction.

## Mood

Peat, fog, held breath, a door left ajar, water that remembers. Cold
world, one warm light.

## Palette - Bog & Bell

Carried by **luminance only** - lighter means more important. No
saturated colors anywhere. Hue is atmosphere; brightness is meaning.

| Role | Name | Hex | Notes |
|---|---|---|---|
| Base | peat-black | `#14130f` | near-black, never pure black |
| Ink | bone-white | `#e8e5df` | body text; ~12:1 on base |
| Dim | moss-grey | `#a39e92` | secondary text, borders |
| Fog | river-grey | `#6b6f66` | distant terrain, mist |
| Moss | bog green | `#4a5442` | vegetation, desaturated |
| Fen | fen-dark | `#1a2018` | deep water, bog, shadow ground |
| Church | shadow-blue | `#2a2e33` | the church and all it owns - cold, never alarming |
| **Accent** | **golden light** | `#c9ad6b` | **the only warm color in the world** |

### The Gold Rule

Gold appears only when the world is kind. the wanderer's name spoken. The
golden light's words arriving. A door held open. If gold is on
screen, something warm is happening - so gold is almost never on
screen. Its rarity is its voice.

## Tiles

- **32x32** - modern pixel-art size. Room for readable faces, items,
  and expressions; scales cleanly to big screens; easier to parse
  dense scenes.
- Chunky outlines, high edge contrast. Tiles must read at 1x and 2x.
- Avoid single-pixel noise: fog and water animate by *shifting*, not
  flickering.

## Typography

- Body text: serif (Georgia or system serif). No all-caps for meaning.
- Line height 1.6+, generous letter spacing in dense blocks.
- Pixel fonts only for headers, never for body text.

## Motion

- No motion by default. `prefers-reduced-motion: reduce` is honored
  everywhere.
- No flashing, no pulsing, no glow-animation. The world holds its
  breath; so does the screen.

## Sound (direction only, for later)

Bells, water, wind, one string instrument heard through a wall.
Quiet enough to be almost imagined. The church bell sounds
*schedule*; the bog bell, when it finally sounds, is the only
warm-tuned note in the game.
