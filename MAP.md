# Private Canon - Town Map

> The map is the story's geometry. What the church tower can see is
> what the archive can see. Everything else is freedom, and the map
> says exactly where the freedom lives.

## The Map

```
                       to the archive
                              |
        .---------------------+---------------------.
        |                     |                     |
   THE MILL              THE SQUARE            THE CHURCH ▲
   old wheel on the      inn, market, the      tower above all
   river; grinds slow    whisper-stone         roofs; priest's
        |                     |               house in its shade
   ~~~~ river ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ~~~~
        |                     |
   BLACKFEN              THE BOOKSHOP
   the bog; the bell     her shop + home;
   sleeps in the dark    parish ledgers upstairs;
   water                 one back door, river side
        \                     /
         \___ reed path _____/
              (passable at low
               water only; the
               fox's way)
                   |
            HER MOTHER'S GRAVE
            in the reeds, on no
            parish record
```

## Keyed Locations

| # | Place | Story function |
|---|---|---|
| 1 | **The Church + tower** | the archive's face. The uncle's house in its shade. The tower sees the square, the road, and the bookshop's front door - never the river side. Its bell rings the hours: the schedule of the conserving |
| 2 | **The Bookshop** | Her trade and her shelter. Parish ledgers upstairs (the uncle's arrangement). Back door faces the river - one deliberate step out of every sightline. The light that burned all night is visible from exactly one place: the ferryman's window |
| 3 | **The Square** | Whisper-stone, market, inn. The rumor network's heart. Where she is called "boy" and where, in time, "the wanderer" is first said aloud |
| 4 | **The Mill** | Upstream. Grinds slow. The phase clock - when the wheel completes a season, the world's tone shifts. Nobody remembers who owns it |
| 5 | **Blackfen** | The bog downstream. The tongueless bell sleeps here. Reached by no road; the reed path only |
| 6 | **The Reed Path** | The fox's way. Passable at low water only - crossing is always a choice the player makes, never a cutscene |
| 7 | **Her Mother's Grave** | In the reeds, out of every parish record. The goodbye lives here. When the tongueless bell finally rings, it rings here |

## Sightlines (the mechanics of being watched)

- **The tower sees:** square, road, mill road, bookshop front. The
  conserving gaze.
- **The tower cannot see:** Blackfen, the reed path, the grave, the
  bookshop's back door, the river itself. The whole second half of
  the story happens in the tower's blind spots.
- **The two bells:** the church bell has a tongue and a schedule.
  The bog bell has neither - it waits for a hand. One rings for
  the archive; the other, once, for her.

## Later

When the tile engine exists (phase 2), this map becomes real data:
a grid, tiles, walkability, water levels, and sightline polygons
computed from the tower. `MAP.md` stays the source of truth; the
engine renders what it says.
