  // ---- the living hazards ----
  // Each region's enemies ride in baked (`window.VEFR_ENEMIES`, one
  // list per region). A slain enemy is remembered per region, per
  // world, so a cleared room stays cleared; a wounded one resets on
  // reload. Combat is deterministic: fixed numbers, no randomness, no
  // clock. Enemy sight is Manhattan distance.
  var enemiesByRegion = window.VEFR_ENEMIES || {};
  var enemies = [];

  function slainKey() {
    var w = (window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world';
    return 'vefr-slain-' + w + '-' + regionName;
  }
  // A generated floor remembers its kills in the descent's own save,
  // beside its explored bitset, because a floor that was never baked is
  // not a region name anyone kept a key for.
  function descentOn() {
    return !!(window.VEFR_DESCENT && window.VEFR_DESCENT.isGenerated(regionName));
  }
  function loadSlain() {
    if (descentOn()) return window.VEFR_DESCENT.loadKills();
    var a = store.getJSON(slainKey(), []);
    return Array.isArray(a) ? a : [];
  }
  function saveSlain() {
    if (descentOn()) {
      var names = [];
      for (var i = 0; i < enemies.length; i++) {
        if (enemies[i] && !enemies[i].alive) names.push(enemies[i].id);
      }
      window.VEFR_DESCENT.saveKills(names);
      return;
    }
    var dead = enemies.filter(function (e) { return !e.alive; })
      .map(function (e) { return e.id + '#' + (e.sig || ''); });
    store.setJSON(slainKey(), dead);
  }
  // A monster is remembered by what it *is*, not only by its name: move it,
  // restat it, or regenerate the floor, and it is a new monster again. So a
  // rebuild never leaves a floor mysteriously empty.
  function enemySig(raw) {
    return [raw.name, (Array.isArray(raw.at) ? raw.at.join(',') : ''),
            raw.hp, raw.atk, (Array.isArray(raw.drops) ? raw.drops.join(',') : '')].join('|');
  }
  function loadEnemies() {
    var dead = loadSlain();
    var list = enemiesByRegion[regionName] || [];
    enemies = list.map(function (e) {
      var sig = enemySig(e);
      return {
        id: e.id, name: e.name, sprite: e.sprite || '',
        sig: sig,
        at: Array.isArray(e.at) ? e.at.slice() : [0, 0],
        hp: (typeof e.hp === 'number') ? e.hp : 1,
        // The health it walked in with, kept so "badly hurt" means a
        // third of that and not a number someone typed into a pack.
        hp0: (typeof e.hp === 'number') ? e.hp : 1,
        atk: (typeof e.atk === 'number') ? e.atk : 1,
        sight: (typeof e.sight === 'number') ? e.sight : 6,
        // The xp this foe is worth, in levels mode (design/growth.md).
        // A pack without it reads as zero: defeat still plays as before.
        xp: (typeof e.xp === 'number') ? e.xp : 0,
        drops: Array.isArray(e.drops) ? e.drops.slice() : [],
        alive: dead.indexOf(e.id + '#' + sig) === -1
      };
    });
  }
  function enemyAt(x, y) {
    for (var i = 0; i < enemies.length; i++) {
      var e = enemies[i];
      if (e && e.alive && e.at[0] === x && e.at[1] === y) return e;
    }
    return null;
  }
  function tileOpenForEnemy(x, y) {
    if (y < 0 || x < 0 || y >= town.map.length || x >= town.map[0].length) return false;
    if ((town.legend[town.map[y][x]] || {}).solid) return false;
    if (x === hero[0] && y === hero[1]) return false;
    return !enemyAt(x, y);
  }
  function manhattan(x1, y1, x2, y2) {
    return Math.abs(x1 - x2) + Math.abs(y1 - y2);
  }

