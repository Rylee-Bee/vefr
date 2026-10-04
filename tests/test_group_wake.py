"""E7.3: waking a group, the free turn that follows, noise, and the warden.

ADR 0014 ("Monster AI", JS only) plus its owner decisions of 2026-10-04
add four things to E0d's sleeping monsters:

  1. **Wake-all.** Waking one member of a linked group marks every other
     living member of that group awake in the SAME monster phase. A
     member 14 tiles from the hero - far outside its own wake radius of
     10 and its own sight of 6 - is awake because the group's leader
     woke, and that is what `test_the_group_wakes_all_together` proves.
  2. **Wake grace.** A monster the group's wake caught spends the phase
     it woke in doing nothing and acts from the next one, so a group
     wakes together and never lands its first blow together. A monster
     that woke on its own - in sight, hit, or woken by noise - has no
     free turn and acts at once, which is E0d's behaviour exactly and
     is what keeps `tests/test_monster_sleep.py` green.
  3. **Noise.** A loud thing the hero does wakes every sleeper within
     earshot: fighting 12, doors 6, chests 6, stairs 8, breaking 8
     tiles, measured Chebyshev. Only fighting has a call site in the
     two parts this slice owns (`heroAttack`); the other four are named
     and tested, and their call sites are reported as a gap.
  4. **The warden** is awake and never sleeps, so it hunts before
     anything else on the floor does.

The group ids, the leader mark, the leash and the warden mark are read
by the player off the baked spawn records in `window.VEFR_ENEMIES`.
The baker (`src/vefr/cli.py`) does not carry those keys yet - E7.2 owns
that - so every fixture here weaves the pack the shipped way and then
re-bakes the one `window.VEFR_ENEMIES` literal with the keys the
player's reader already looks for. Nothing else about the player is
touched: these are the real woven player, the real turn loop, the real
flood.

Every fixture is a fixed map with fixed numbers - no randomness, no
wall-clock, no mocks. Run with:

    bash tests/run.sh tests/test_group_wake.py
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from play_kit import pack, play, weave

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not installed")

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "web" / "player" / "parts"

# One big open room: 30x11 with a solid border, the hero starting in the
# corner at [1, 1]. Every tile inside is walkable, so a walking distance
# and a straight line agree and the numbers below can be read off the
# map by eye.
WIDTH, HEIGHT = 30, 11
LEGEND = {".": {"base": ["#212a20"]}, "#": {"base": ["#2a2e33"], "solid": True}}

# ---- the noise table, as the owner fixed it on 2026-10-04 ----
# kind -> radius in tiles, Chebyshev from the hero.
NOISE = {"fight": 12, "door": 6, "chest": 6, "stair": 8, "break": 8}

# ---- the fixtures ----

# A group of three, well east of the hero, all of it asleep at the
# start. The leader's spawn tile is the group's home. Every member has
# the default sight of 6, so each one's own wake radius is the default
# 10 and E0d's Manhattan rule and the ADR's Chebyshev sight rule agree
# about every tile in this fixture.
GROUP = [
    {"id": "g1-leader", "name": "a group leader", "at": [20, 1],
     "hp": 4, "atk": 1, "sprite": "rat",
     "group": "g1", "leader": True, "leash": 3},
    {"id": "g1-kin-a", "name": "a group kin", "at": [22, 1],
     "hp": 4, "atk": 1, "sprite": "rat", "group": "g1"},
    {"id": "g1-kin-b", "name": "another group kin", "at": [23, 1],
     "hp": 4, "atk": 1, "sprite": "rat", "group": "g1"},
]

# A fight next to the hero and one sleeper ten tiles up the row: 11
# tiles away, which is one tile past E0d's wake radius of 10 and five
# tiles past its sight of 6, and four tiles inside the fighting noise
# radius of 12. Nothing but the noise can wake it.
FIGHT = [
    {"id": "bump-target", "name": "a bump target", "at": [2, 1],
     "hp": 4, "atk": 1, "sprite": "rat"},
    {"id": "far-ear", "name": "a far ear", "at": [12, 1],
     "hp": 4, "atk": 1, "sight": 6, "sprite": "rat"},
]

# The warden and one ordinary monster two tiles west of it. The hero
# ends this fixture at [2, 1], so the guard is twelve tiles away -
# outside the wake radius of 10, and far outside its sight of 6 - and it
# is asleep. The warden is fourteen tiles away, which is further still,
# and it is awake. The warden has sight 6, so the hero is out of its
# sight and it drifts the way any awake monster out of sight does:
# toward the nearest other living monster, the sleeping guard.
WARDEN = [
    {"id": "hall-warden", "name": "the hall warden", "at": [16, 1],
     "hp": 4, "atk": 1, "sight": 6, "sprite": "rat", "warden": True},
    {"id": "hall-guard", "name": "a hall guard", "at": [14, 1],
     "hp": 4, "atk": 1, "sight": 6, "sprite": "rat"},
]

READS = [
    "VEFR_COMBAT.hero.at", "VEFR_COMBAT.hero.hp",
    "VEFR_COMBAT.enemies.0.at", "VEFR_COMBAT.minds.0.awake",
    "VEFR_COMBAT.enemies.1.at", "VEFR_COMBAT.minds.1.awake",
    "VEFR_COMBAT.enemies.2.at", "VEFR_COMBAT.minds.2.awake",
    "text:#combat-live",
]


def open_room(tmp_path, enemies):
    """The combat fixture with its town swapped for the big open room.
    The act keeps its regions; only the town's map, contract and enemies
    are the test's own. The hero starts in the corner at [1, 1]."""
    p = pack(tmp_path, "combat")
    town = p / "acts" / "act-1" / "town"
    wall = "#" * WIDTH
    row = "#" + "." * (WIDTH - 2) + "#"
    rows = [wall] + [row] * (HEIGHT - 2) + [wall]
    (town / "map.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    contract = {
        "tile": 32, "bg": "#131311", "hero_start": [1, 1],
        "sanctuary_tiles": ["."],
        "water_by_phase": {"dusk": "low", "dawn": "low"},
        "flood_tiles": [], "pois": {}, "legend": LEGEND,
        "enemies": enemies,
    }
    (town / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return p


def woven_with_minds(pack_dir, tmp_path, roster):
    """Weave `pack_dir` and re-bake `window.VEFR_ENEMIES` with `roster`.

    The pack is woven the shipped way. The one edit is the baked enemies
    literal, so the group keys reach the player: the baker closes the
    spawn record to the fields E7.1 wrote, and the player's group reader
    looks for `group`, `leader`, `leash` and `warden` on that same
    record. When the baker carries them (E7.2) this helper goes away and
    the fixtures read as they are written.
    """
    html = Path(weave(pack_dir, tmp_path)).read_text(encoding="utf-8")
    marker = "window.VEFR_ENEMIES = "
    at = html.index(marker) + len(marker)
    baked, end = json.JSONDecoder().raw_decode(html, at)
    baked["town"] = roster
    out = Path(tmp_path) / "minds.html"
    out.write_text(html[:at] + json.dumps(baked) + html[end:], encoding="utf-8")
    return out


def walk_right(n):
    return ["begin", "walk:" + ",".join(["right"] * n)]


# ---- 1. wake-all and the free turn ----

def test_the_group_wakes_all_together(tmp_path):
    html = woven_with_minds(open_room(tmp_path, GROUP), tmp_path, GROUP)
    # Nine steps: the hero stands at [10, 1], ten tiles from the leader -
    # exactly its wake radius, so the leader is awake - and twelve and
    # thirteen tiles from the two kins, well outside both of their own
    # wake radii and sights. Nothing else can wake them.
    out = play(html, {"steps": walk_right(9), "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [10, 1]
    assert reads["VEFR_COMBAT.minds.0.awake"] is True, \
        "the hero ended a turn inside the leader's wake radius"
    assert reads["VEFR_COMBAT.minds.1.awake"] is True, \
        "a group member wakes with the group, not with the hero's radius"
    assert reads["VEFR_COMBAT.minds.2.awake"] is True, \
        "the far member wakes in the same phase as the one in earshot"
    # The leader woke on its own and acted at once: ten tiles out is
    # outside its sight of 6, so it walks home, and it is already home.
    assert reads["VEFR_COMBAT.enemies.0.at"] == [20, 1]
    # The two kins woke by the group and spent the free turn: they are
    # exactly where they spawned. This is the grace, and it is also the
    # proof that the group's wake reached 12 and 13 tiles.
    assert reads["VEFR_COMBAT.enemies.1.at"] == [22, 1], \
        "a member woken by its group does not act on the turn it woke"
    assert reads["VEFR_COMBAT.enemies.2.at"] == [23, 1], \
        "the far member is awake and still exactly where it spawned"
    assert reads["VEFR_COMBAT.hero.hp"] == 3, \
        "nothing struck the hero on the turn the group woke"


def test_the_free_turn_is_spent_and_the_group_acts_next(tmp_path):
    html = woven_with_minds(open_room(tmp_path, GROUP), tmp_path, GROUP)
    # One step further: the hero is at [11, 1] and the free turn is
    # spent. Both kins are out of sight, so each walks one tile home -
    # the leader's spawn tile is [20, 1] and a member stops within one
    # tile of it, so the nearer kin stops at [21, 1] and the further one
    # at [22, 1].
    out = play(html, {"steps": walk_right(10), "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [11, 1]
    assert reads["VEFR_COMBAT.enemies.1.at"] == [21, 1], \
        "the nearer kin acts the turn after the one it woke on"
    assert reads["VEFR_COMBAT.enemies.2.at"] == [22, 1], \
        "the further kin acts too, so the group moves as one"
    assert all(reads[f"VEFR_COMBAT.minds.{i}.awake"] for i in range(3))


def test_a_lone_monster_wakes_and_acts_on_the_same_turn(tmp_path):
    """The guard on the grace rule: the free turn belongs to the group
    wake, not to waking at all. A monster that wakes on its own acts at
    once - E0d's rule, and the reason tests/test_monster_sleep.py still
    passes. The two monsters here stand where the group's members stood
    and are the same shape; only the group id is missing."""
    alone = [
        {"id": "solo-leader", "name": "a lone leader", "at": [20, 1],
         "hp": 4, "atk": 1, "sprite": "rat"},
        {"id": "solo-kin", "name": "a lone kin", "at": [22, 1],
         "hp": 4, "atk": 1, "sprite": "rat"},
    ]
    html = woven_with_minds(open_room(tmp_path, alone), tmp_path, alone)
    out = play(html, {"steps": walk_right(9), "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.minds.0.awake"] is True
    # Ten tiles out, so it is awake and out of its own sight: it drifts
    # one tile toward the nearest other monster, the way an awake
    # monster out of sight always has. It acted on the turn it woke.
    assert reads["VEFR_COMBAT.enemies.0.at"] == [21, 1], \
        "a monster that woke on its own has no free turn"
    # The second one is twelve tiles out, outside even the wake radius,
    # so with no group to wake it there it sleeps exactly as it did
    # before this slice: a lone monster keeps today's behaviour.
    assert reads["VEFR_COMBAT.minds.1.awake"] is False, \
        "with no group id there is nothing to spread a wake to"
    assert reads["VEFR_COMBAT.enemies.1.at"] == [22, 1]


# ---- 2. noise ----

def test_fighting_wakes_a_sleeper_out_of_sight_and_out_of_range(tmp_path):
    """The hero bumps the monster next to it. A fight is 12 tiles of
    noise, so the sleeper at [12, 1] - Chebyshev 11 from the hero, one
    tile past E0d's Manhattan wake radius of 10 and five past its own
    sight of 6 - wakes, and acts at once because the hero's turn is not
    a monster phase."""
    html = woven_with_minds(open_room(tmp_path, FIGHT), tmp_path, FIGHT)
    out = play(html, {"steps": ["begin", "walk:right"], "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [1, 1], "the bump does not move the hero"
    assert reads["VEFR_COMBAT.enemies.0.at"] == [2, 1]
    assert reads["VEFR_COMBAT.minds.1.awake"] is True, \
        "a fight 11 tiles away is inside the 12-tile noise radius"
    assert reads["VEFR_COMBAT.enemies.1.at"] == [11, 1], \
        "a monster woken by noise acts on the hero's turn, not a turn later"


def test_walking_away_leaves_the_same_sleeper_asleep(tmp_path):
    """The control for the noise test: the same two monsters, the same
    hero, one turn spent - and no fight. The sleeper at [12, 1] is now
    Chebyshev 12 from a hero at [1, 2], so even the fighting radius does
    not reach it, and it stays exactly where it spawned."""
    html = woven_with_minds(open_room(tmp_path, FIGHT), tmp_path, FIGHT)
    out = play(html, {"steps": ["begin", "walk:down"], "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [1, 2]
    assert reads["VEFR_COMBAT.minds.1.awake"] is False, \
        "a quiet turn wakes nobody"
    assert reads["VEFR_COMBAT.enemies.1.at"] == [12, 1]


# ---- the five loud events, straight at the reader ----

# The three AI parts verbatim, in a node vm, with the rest of the player
# stubbed the way tests/browser/bench_floor_play.py stubs it for the
# same measurement. Nothing here rewrites the engine: `noiseRadius` and
# `makeNoise` are the shipped functions, called directly, because four
# of the five loud events happen in a part this slice does not own and
# so have no in-player route to prove.
NOISE_DRIVER = """
import fs from 'node:fs';
import vm from 'node:vm';

const partsDir = process.argv[2];
const spec = JSON.parse(process.argv[3]);
const parts = ['410-the-living-hazards.js', '420-how-a-monster-thinks.js',
               '430-loot-on-the-floor.js']
  .map(n => fs.readFileSync(partsDir + '/' + n, 'utf8')).join('\\n');

const size = spec.size;
const wall = '#'.repeat(size);
const row = '#' + '.'.repeat(size - 2) + '#';
const rows = [wall];
for (let i = 0; i < size - 2; i++) rows.push(row);
rows.push(wall);

const sandbox = {
  window: { VEFR_WORLD: { name: 'noise' } },
  document: {},
  store: { get: () => null, set: () => {},
           getJSON: (k, d) => d, setJSON: () => {} },
  regionName: 'noise',
  town: { map: rows, legend: { '#': { solid: true } }, hero_start: [1, 1] },
  hero: [1, 1], HERO_HP: 9, DEATH_LINE: 'down', XP_WORD: 'renown',
  draw() {}, flushGrowth() {}, sayGrowth() {}, practiceSuffix: s => s,
  combatSay() {}, soundCue() {}, saveHeroHp() {}, renderHp() {},
  heroMax: () => 9, heroAtk: () => 2, heroGold: () => 0,
  bagItems: () => [], bagAdd: () => false, itemName: () => '',
  itemCatalog: () => ({}), fireRule() {}, growBump: () => 1,
  growAward: () => null, levelSuffix: () => '', enterRegion() {},
};
sandbox.window.VEFR_ENEMIES = {};
vm.createContext(sandbox);
vm.runInContext(parts, sandbox);

const out = { radii: {}, kinds: {} };
for (const kind of Object.keys(spec.kinds)) {
  out.radii[kind] = sandbox.noiseRadius(kind);
  out.kinds[kind] = [];
  for (const at of spec.kinds[kind]) {
    const roster = [{ id: 'ear', name: 'an ear', at: at.slice(),
                      hp: 4, atk: 1, sight: 6, drops: [] }];
    sandbox.window.VEFR_ENEMIES = { noise: roster };
    sandbox.enemiesByRegion = { noise: roster };
    sandbox.loadEnemies();
    sandbox.prepareMinds();
    sandbox.makeNoise(kind);
    out.kinds[kind].push({ at: at, awake: sandbox.enemies[0].awake });
  }
}
console.log(JSON.stringify(out));
"""


def noise_read(tmp_path, spec):
    driver = Path(tmp_path) / "noise_driver.mjs"
    driver.write_text(NOISE_DRIVER, encoding="utf-8")
    run = subprocess.run(["node", str(driver), str(PARTS), json.dumps(spec)],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_the_five_loud_events_carry_the_owners_radii(tmp_path):
    """One number per loud event, in one place, each reachable on its
    own: fighting 12, doors and chests 6, stairs and breaking 8. The
    boundary is measured on the diagonal, so a rule that counted
    straight-line-plus would call every one of these tiles out of
    earshot and fail."""
    kinds = {}
    for kind, radius in NOISE.items():
        # [1, 1] + (radius, radius) is Chebyshev `radius` and Manhattan
        # twice that; one tile further is one tile out of earshot.
        kinds[kind] = [[1 + radius, 1 + radius], [2 + radius, 2 + radius]]
    out = noise_read(tmp_path, {"size": 40, "kinds": kinds})
    for kind, radius in NOISE.items():
        assert out["radii"][kind] == radius, \
            f"the {kind} noise radius is {radius} tiles"
        heard = out["kinds"][kind]
        assert heard[0]["awake"] is True, \
            f"a {kind} {radius} tiles away is inside earshot"
        assert heard[1]["awake"] is False, \
            f"a {kind} {radius + 1} tiles away is not"


def test_an_unknown_loud_event_carries_nothing(tmp_path):
    """A kind nobody declared is not a noise: the table is closed, so a
    typo in a call site wakes nobody rather than waking the floor."""
    out = noise_read(tmp_path, {"size": 20, "kinds": {"sneeze": [[1, 3], [1, 4]]}})
    assert out["radii"].get("sneeze") in (None, 0)
    assert [e["awake"] for e in out["kinds"]["sneeze"]] == [False, False]


# ---- 3. the warden ----

def test_the_warden_is_awake_and_the_guard_beside_it_is_not(tmp_path):
    """The warden does not sleep. The hero is fourteen tiles from it, so
    the sleeping rule would have it asleep - and `hall-guard`, two tiles
    nearer the hero and two from the warden, is asleep too, which is what
    makes the warden's wake its own doing. Awake and out of the hero's
    sight, it drifts toward the nearest other living monster, the way
    any awake monster out of sight has always done."""
    html = woven_with_minds(open_room(tmp_path, WARDEN), tmp_path, WARDEN)
    out = play(html, {"steps": ["begin", "walk:right"], "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [2, 1]
    assert reads["VEFR_COMBAT.minds.0.awake"] is True, \
        "the warden is awake without the hero ever coming near it"
    assert reads["VEFR_COMBAT.enemies.0.at"] == [15, 1], \
        "an awake warden out of sight hunts toward the nearest monster"
    assert reads["VEFR_COMBAT.minds.1.awake"] is False, \
        "the guard beside it is an ordinary sleeper and stays asleep"
    assert reads["VEFR_COMBAT.enemies.1.at"] == [14, 1]
