"""E7.3: the leash. A group goes as far as its home allows, and no further.

ADR 0014, "Leash":

  - a group's home is its leader's spawn tile;
  - on floor load the game floods once from home, cut off at
    `leash + 1` steps, and keeps the result in memory (never saved);
  - a member never steps onto a tile further than `leash` from home,
    and at that edge it attacks an adjacent hero and otherwise holds;
  - when the hero is out of the member's sight, the member walks home
    until it is within one tile of home, then idles awake;
  - a lone monster and an elite keep today's behaviour exactly.

The leash is measured by WALKING distance, not by the straight line,
so the fixtures here use one big open room where the two agree and
every number can be read off the map: 30x11, the hero in the corner
at [1, 1], the group's home at [20, 1] and a leash of 3, so the edge is
[17, 1] and a member may not stand west of it.

  turn  9  hero [10, 1]  the leader is 10 tiles out: awake, walking home
  turn 13  hero [14, 1]  the leader is inside its sight of 6 at last and
                         steps west: [19, 1]
  turn 14  hero [15, 1]  [18, 1]
  turn 15  hero [16, 1]  [17, 1] - the edge, one tile from the hero
  turn 16  hero [16, 2]  it would step to [16, 1], which is 4 from home.
                         It is at the edge, the hero is not adjacent, so
                         it holds: the leash is what stopped it, and it
                         is the only thing that could have.

Every assertion is checked against the game's own tile as well as
against a distance walked in this file, so a member that stepped
through a wall or off the map would fail here too.

The group ids, the leader mark and the leash ride on the baked spawn
records in `window.VEFR_ENEMIES`, and the baker carries them there: a
fixture here is a real pack with the roster in its region's own
contract, woven the shipped way. Nothing else about the player is
touched.

Every fixture is a fixed map with fixed numbers - no randomness, no
wall-clock, no mocks. Run with:

    bash tests/run.sh tests/test_group_leash.py
"""

import json
import shutil
from collections import deque

import pytest

from play_kit import pack, play, weave

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not installed")

WIDTH, HEIGHT = 30, 11
LEGEND = {".": {"base": ["#212a20"]}, "#": {"base": ["#2a2e33"], "solid": True}}

# The group's home, and the leash it walks on. Three tiles: the edge is
# [17, 1], and nothing in the group may stand west of it.
HOME = [20, 1]
LEASH = 3

# The group the whole file watches: the leader on its own spawn tile
# (which is home), one kin three tiles south of it and one three tiles
# east, so the three of them walk home down three different rows and
# stop on three different tiles. Every member has the default sight of
# 6, so E0d's Manhattan wake radius of 10 and the ADR's Chebyshev sight
# rule agree here.
GROUP = [
    {"id": "g1-leader", "name": "a group leader", "at": [20, 1],
     "hp": 4, "atk": 1, "sprite": "rat",
     "group": "g1", "leader": True, "leash": LEASH},
    {"id": "g1-kin-a", "name": "a group kin", "at": [20, 4],
     "hp": 4, "atk": 1, "sprite": "rat", "group": "g1"},
    {"id": "g1-kin-b", "name": "another group kin", "at": [23, 1],
     "hp": 4, "atk": 1, "sprite": "rat", "group": "g1"},
]

# A second group that names no leader, so its home is the lowest-sorted
# id among its living members: "kin-a" at [28, 1]. Its other member
# starts two tiles west of that and may walk one tile further west, to
# [25, 1], and no further.
NO_LEADER = [
    {"id": "kin-b", "name": "a kin", "at": [26, 1],
     "hp": 4, "atk": 1, "sprite": "rat", "group": "g2", "leash": LEASH},
    {"id": "kin-a", "name": "another kin", "at": [28, 1],
     "hp": 4, "atk": 1, "sprite": "rat", "group": "g2"},
]

# Two monsters with no group at all. They are the guard on the last
# line of the ADR: a lone monster keeps today's behaviour, so nothing
# holds it to a home. Awake and out of the hero's sight, each drifts
# toward the nearest other living monster, and neither of them ever
# walks back to the tile it spawned on.
LONE = [
    {"id": "no-group-a", "name": "a no group", "at": [20, 1],
     "hp": 4, "atk": 1, "sight": 6, "sprite": "rat"},
    {"id": "no-group-b", "name": "another no group", "at": [23, 1],
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


def walk_right(n):
    return ["begin", "walk:" + ",".join(["right"] * n)]


def walkable():
    """The room's walkable tiles, as the one key shape the player uses."""
    wall = "#" * WIDTH
    row = "#" + "." * (WIDTH - 2) + "#"
    rows = [wall] + [row] * (HEIGHT - 2) + [wall]
    return {(x, y) for y, line in enumerate(rows) for x, ch in enumerate(line)
            if ch != "#"}


def steps_from_home(at, home=HOME):
    """How far `at` is from `home` by walking, the count the leash is
    measured in. Breadth-first over the real map, so a fixture that put
    a member behind a wall would be caught here as well as in the game.
    """
    open_tiles = walkable()
    seen = {tuple(home): 0}
    queue = deque([tuple(home)])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nxt = (x + dx, y + dy)
            if nxt in seen or nxt not in open_tiles:
                continue
            seen[nxt] = seen[(x, y)] + 1
            queue.append(nxt)
    assert tuple(at) in seen, f"{at} is not a walkable tile of the room"
    return seen[tuple(at)]


def assert_inside_leash(reads, ids, leash=LEASH):
    for i, name in enumerate(ids):
        at = reads[f"VEFR_COMBAT.enemies.{i}.at"]
        assert steps_from_home(at) <= leash, \
            f"{name} stands at {at}, {steps_from_home(at)} tiles from home"


# ---- 1. the edge ----

def test_a_member_stops_on_the_leash_and_holds_there(tmp_path):
    html = weave(open_room(tmp_path, GROUP), tmp_path)
    # Fifteen steps east: the leader has come three tiles west of home,
    # which is the leash, and the hero is next to it.
    walked = play(html, {"steps": walk_right(15), "read": READS})
    assert walked["errors"] == []
    reads = walked["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [16, 1]
    assert reads["VEFR_COMBAT.enemies.0.at"] == [17, 1], \
        "the leader walks west until it is exactly on the leash"
    assert steps_from_home([17, 1]) == LEASH
    # One step down and the leader is two tiles from a hero it can see
    # (Manhattan 2, well inside its sight of 6). It is on the edge, the
    # hero is not adjacent, so it holds: without the leash the next step
    # west would have taken it to [16, 1], four tiles from home.
    held = play(html, {"steps": walk_right(15) + ["walk:down"], "read": READS})
    assert held["errors"] == []
    reads = held["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [16, 2]
    assert reads["VEFR_COMBAT.enemies.0.at"] == [17, 1], \
        "at the edge a member attacks an adjacent hero and otherwise holds"
    assert reads["VEFR_COMBAT.hero.hp"] == 3, "it never reached the hero"
    # The whole group is inside the leash, and awake: the hero is in the
    # room, so nothing here fell asleep again.
    assert_inside_leash(reads, ["leader", "kin-a", "kin-b"])
    assert all(reads[f"VEFR_COMBAT.minds.{i}.awake"] for i in range(3))


def test_no_member_ever_stands_past_the_leash(tmp_path):
    """The invariant, sampled turn by turn across the whole approach and
    the walk away again. The leader is the one that wants to leave: it
    is woken, it can see the hero, and it is held."""
    html = weave(open_room(tmp_path, GROUP), tmp_path)
    steps = ["begin"]
    east = 15
    for _ in range(east):
        steps.append("walk:right")
        out = play(html, {"steps": list(steps), "read": READS})
        assert out["errors"] == []
        assert_inside_leash(out["reads"], ["leader", "kin-a", "kin-b"])
    # And back west, out of sight and home again, sampled the same way.
    for _ in range(15):
        steps.append("walk:left")
        out = play(html, {"steps": list(steps), "read": READS})
        assert out["errors"] == []
        assert_inside_leash(out["reads"], ["leader", "kin-a", "kin-b"])


# ---- 2. going home ----

def test_the_group_walks_home_and_idles_awake(tmp_path):
    html = weave(open_room(tmp_path, GROUP), tmp_path)
    # Fifteen east and four south puts the hero at [16, 5], within the
    # leader's sight of 6 but not adjacent, and the leader is still on
    # the edge holding.
    away = play(html, {"steps": walk_right(15) + ["walk:" + ",".join(["down"] * 4)],
                       "read": READS})
    assert away["errors"] == []
    assert away["reads"]["VEFR_COMBAT.hero.at"] == [16, 5]
    assert steps_from_home(away["reads"]["VEFR_COMBAT.enemies.0.at"]) == LEASH, \
        "with the hero below it the leader is still on the edge, holding"
    # Thirteen east and thirteen west. The hero comes no closer than six
    # tiles to the two kins, so they never leave home: they walk the two
    # tiles the group wake sent them walking and stop. The leader is
    # pulled out to the edge, loses the hero as the hero walks back
    # west, and walks home after it - stopping one tile short of [20, 1],
    # which is what "within one tile of home" means.
    steps = walk_right(13) + ["walk:" + ",".join(["left"] * 13)]
    home = play(html, {"steps": steps, "read": READS})
    assert home["errors"] == []
    reads = home["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [1, 1]
    for i, name in enumerate(["leader", "kin-a", "kin-b"]):
        at = reads[f"VEFR_COMBAT.enemies.{i}.at"]
        assert steps_from_home(at) <= 1, \
            f"{name} stopped at {at}, not within one tile of home"
    assert reads["VEFR_COMBAT.enemies.0.at"] == [19, 1], \
        "the member that was pulled out is the one that walked back"
    # Awake, and awake to stay: the hero is nineteen tiles away and the
    # group does not fall asleep. Two more turns away from home change
    # nothing at all.
    assert all(reads[f"VEFR_COMBAT.minds.{i}.awake"] for i in range(3))
    after = play(html, {"steps": steps + ["walk:down", "walk:up"], "read": READS})
    assert after["errors"] == []
    for i in range(3):
        assert after["reads"][f"VEFR_COMBAT.enemies.{i}.at"] == \
            reads[f"VEFR_COMBAT.enemies.{i}.at"], \
            "a group that is home and awake idles where it stands"
        assert after["reads"][f"VEFR_COMBAT.minds.{i}.awake"] is True, \
            "home is not sleep: an idling group is still awake"


# ---- 3. whose home it is, and who is not leashed at all ----

def test_a_group_with_no_leader_mark_uses_its_lowest_sorted_id(tmp_path):
    """No member says `leader: true`, so home is the lowest-sorted id -
    "kin-a" at [28, 1]. Its pack-mate starts two tiles west, comes up
    against the hero, and stops on the leash three tiles from that home
    with the hero two tiles away and well inside its sight."""
    html = weave(open_room(tmp_path, NO_LEADER), tmp_path)
    out = play(html, {"steps": walk_right(23), "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [24, 1]
    assert reads["VEFR_COMBAT.enemies.0.at"] == [25, 1], \
        "with no leader mark the lowest id is home, and the leash is real"
    assert steps_from_home(reads["VEFR_COMBAT.enemies.0.at"], [28, 1]) == LEASH
    # The member that is home is leashed too: it can see the hero from
    # its own spawn tile, so it comes two tiles out and stops there
    # because the next tile west is its pack-mate, already on the line.
    assert reads["VEFR_COMBAT.enemies.1.at"] == [26, 1], \
        "the member that is home is held by the same leash"
    assert steps_from_home(reads["VEFR_COMBAT.enemies.1.at"], [28, 1]) == 2


def test_a_lone_monster_is_neither_leashed_nor_sent_home(tmp_path):
    """The last line of the ADR: a lone monster and an elite keep
    today's behaviour exactly. Wake one of these two the way the group
    above is woken - the hero ends a turn ten tiles away - and it does
    not stop at three tiles from its spawn. It walks AWAY, east, toward
    the other monster, because that is what an awake monster out of the
    hero's sight has always done. A group member would have turned
    around and gone home instead."""
    html = weave(open_room(tmp_path, LONE), tmp_path)
    out = play(html, {"steps": walk_right(14), "read": READS})
    assert out["errors"] == []
    reads = out["reads"]
    assert reads["VEFR_COMBAT.hero.at"] == [15, 1]
    assert reads["VEFR_COMBAT.enemies.0.at"] == [22, 1], \
        "a lone monster is not leashed: it walks toward its nearest ally"
    assert reads["VEFR_COMBAT.minds.0.awake"] is True
    # The second one woke when the hero came inside its own wake radius
    # and has nowhere to go: its ally is on the tile it would step onto,
    # so it stands nose to nose, as two of them always have.
    assert reads["VEFR_COMBAT.minds.1.awake"] is True
    assert reads["VEFR_COMBAT.enemies.1.at"] == [23, 1], \
        "an awake monster with its ally in the way holds its tile"
