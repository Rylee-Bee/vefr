  // ---- loot on the floor ----
  // A killed enemy leaves what it carried on the tile it died on; the
  // floor is remembered per world (`vefr-floor-<world>`, one list of
  // {region, at, item}) so leaving and coming back is honest about what
  // is still lying there. Taking a drop removes it. No weight, no use,
  // no drop, no sell, no identifying - this is the first slice only.
  var floor = [];

  function floorKey() {
    var w = (window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world';
    return 'vefr-floor-' + w;
  }
  function loadFloor() {
    var a = store.getJSON(floorKey(), []);
    floor = Array.isArray(a) ? a.filter(function (d) {
      return d && typeof d.item === 'string' && typeof d.region === 'string'
        && Array.isArray(d.at) && d.at.length === 2 && itemCatalog()[d.item];
    }) : [];
  }
  function saveFloor() {
    store.setJSON(floorKey(), floor);
  }
  function dropsAt(x, y) {
    return floor.filter(function (d) {
      return d.region === regionName && d.at[0] === x && d.at[1] === y;
    });
  }
  // Leave a killed enemy's drops where it died. Only a catalog item is
  // placed; the bake already dropped an unknown id.
  function placeDrops(at, ids) {
    var added = false;
    (ids || []).forEach(function (id) {
      if (!itemCatalog()[id]) return;
      floor.push({ region: regionName, at: [at[0], at[1]], item: id });
      added = true;
    });
    if (added) saveFloor();
  }
  // Walking onto a drop takes every item lying on that tile. One plain
  // line says what was taken; the bag panel and the strip redraw.
  function takeHere() {
    var here = dropsAt(hero[0], hero[1]);
    if (!here.length) return;
    var names = [];
    // One `picks-up` per item actually bagged - a drop bagAdd refused
    // (an id the catalog lost) is not picked up and fires nothing.
    here.forEach(function (d) {
      if (bagAdd(d.item)) {
        names.push(itemName(d.item));
        fireRule('picks-up', { what: d.item });
      }
    });
    floor = floor.filter(function (d) {
      return !(d.region === regionName
        && d.at[0] === hero[0] && d.at[1] === hero[1]);
    });
    saveFloor();
    if (names.length) {
      soundCue('pickup');
      combatSay('You pick up ' + names.join(', ') + '.');
    }
  }

  // A hero bump: strike the enemy on the tile you tried to walk into.
  function heroAttack(e) {
    var dmg = heroAtk();
    e.hp = Math.max(0, e.hp - dmg);
    soundCue('hit');
    var said = 'You hit ' + e.name + ' for ' + dmg + '.';
    // A landed blow is one practice count; levels mode ignores it.
    sayGrowth(practiceSuffix(growBump('strikes')));
    if (e.hp <= 0) {
      e.alive = false;
      saveSlain();
      soundCue('defeat');
      placeDrops(e.at, e.drops);
      fireRule('defeats', { what: e.id });
      said += ' ' + e.name + ' falls.';
      // The defeat line first, then the xp it was worth, then any level.
      var r = growAward(e.xp);
      if (typeof e.xp === 'number' && e.xp > 0) {
        sayGrowth('You earn ' + e.xp + ' ' + XP_WORD + '.');
      }
      if (r && r.grew && r.levelsGained) soundCue('level');
      sayGrowth(levelSuffix(r));
    }
    combatSay(said);
    combatSnapshot();
  }
  // One enemy's attack: the hero loses its `atk`, clamped at zero.
  function enemyAttack(e) {
    HERO_HP = Math.max(0, HERO_HP - e.atk);
    saveHeroHp();
    renderHp();
    combatSay(e.name + ' hits you for ' + e.atk + '.');
    // A hit that reaches the hero is one practice count.
    sayGrowth(practiceSuffix(growBump('hits-taken')));
    soundCue('hurt');
    if (HERO_HP <= 0) { cozyDeath(); return true; }
    return false;
  }
  // How near the hero a monster wakes: its own sight when that runs
  // past ten, ten otherwise. Asleep costs a turn nothing at all -
  // no flood, no step, no attack.
  function wakeRadius(e) { return Math.max(10, e.sight || 0); }
  function asleep(e) {
    return manhattan(e.at[0], e.at[1], hero[0], hero[1]) > wakeRadius(e);
  }
  // A monster's group wakes with it. Nothing carries a group id
  // yet, so this spreads the wake to nobody; it is the seam for
  // when one does.
  function wakeGroup(e, awake) { return awake; }
  // One enemy's turn. Next to the hero -> hit them. Badly hurt with
  // the hero in sight -> step away down the map. In sight -> step one
  // tile closer, the short way round the floor rather than into a wall.
  // Out of sight -> drift toward the nearest other monster, so a pack
  // stays a pack instead of scattering into corners. Alone and out of
  // sight -> it holds still.
  function enemyAct(e, maps) {
    var d = manhattan(e.at[0], e.at[1], hero[0], hero[1]);
    if (d === 1) return enemyAttack(e);
    if (d <= e.sight) {
      if (badlyHurt(e)) return stepAlong(e, distances(maps, hero[0], hero[1]), -1);
      return stepAlong(e, distances(maps, hero[0], hero[1]), 1);
    }
    var ally = nearestAlly(e, maps);
    if (!ally) return false;
    return stepAlong(e, distances(maps, ally.at[0], ally.at[1]), 1);
  }
  // Every living enemy takes its turn in order, against the same
  // shared distance maps; an asleep one costs nothing and is skipped.
  // The hero's death ends the turn early (and wakes them elsewhere).
  function enemyTurn() {
    // The harness reads this once, at the end of a run, so it is
    // reset per turn, not per flood: it always shows the last turn.
    window.VEFR_FLOOD_STATS = { floods: 0, tiles: 0, maxSpan: 0 };
    var roster = enemies.slice();
    var maps = turnMaps();
    // The flood only has to reach a little past the farthest wake:
    // every awake monster stands within its own wake radius of the
    // hero, and the flood reaches wakeRadius + 4 tiles from wherever
    // it starts, so no step an awake monster could take before is
    // lost. Known limit: a monster whose walk the long way round runs
    // farther than this can now hold still where it used to keep
    // coming.
    var far = 10;
    for (var j = 0; j < roster.length; j++) {
      if (roster[j].alive) far = Math.max(far, wakeRadius(roster[j]));
    }
    floodLimit = far + 4;
    // Who acts: awake by the wake radius, asked through the group
    // seam - a later slice adds group ids in wakeGroup alone.
    var awake = [];
    for (var k = 0; k < roster.length; k++) {
      if (!roster[k].alive) continue;
      awake[k] = wakeGroup(roster[k], !asleep(roster[k]));
    }
    for (var i = 0; i < roster.length; i++) {
      if (!roster[i].alive || !awake[i]) continue;
      if (enemyAct(roster[i], maps)) {
        flushGrowth(); draw(); combatSnapshot(); return;
      }
    }
    flushGrowth();
    draw();
    combatSnapshot();
  }
  // Death is Cozy: health back to max, one plain line, and a wake at
  // the hero's baked wake point. Nothing is lost.
  function cozyDeath() {
    combatSay(DEATH_LINE);
    HERO_HP = heroMax();
    saveHeroHp();
    renderHp();
    var wake = (window.VEFR_HERO && window.VEFR_HERO.wake) || {};
    if (wake.region && regions[wake.region]) {
      enterRegion(wake.region, wake.at);
    } else {
      hero = (town.hero_start || [1, 1]).slice();
      loadEnemies();
      draw();
    }
    combatSnapshot();
  }
  // A harness-readable snapshot of the fight, refreshed every turn
  // (precedent: window.VEFR_DESK_LAST).
  function combatSnapshot() {
    window.VEFR_COMBAT = {
      region: regionName,
      hero: { hp: HERO_HP, max: heroMax(), atk: heroAtk(), at: hero.slice() },
      gold: heroGold(),
      enemies: enemies.map(function (e) {
        return { id: e.id, at: e.at.slice(), hp: e.hp, atk: e.atk,
                 sight: e.sight, alive: e.alive };
      }),
      bag: bagItems(),
      floor: floor.filter(function (d) { return d.region === regionName; })
        .map(function (d) {
          return { at: d.at.slice(), item: d.item, name: itemName(d.item) };
        })
    };
    return window.VEFR_COMBAT;
  }
  // The bag and gold code lives outside this closure; give it a way to
  // refresh the snapshot after a change, so the harness always reads
  // the current fight (precedent: window.VEFR_DESK_LAST).
  window.refreshCombatSnapshot = combatSnapshot;

